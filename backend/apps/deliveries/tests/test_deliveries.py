"""Delivery tests: schedule generation, status transitions, skip, pause, kitchen counts, isolation (D-12)."""

import datetime
from datetime import timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.deliveries.models import Delivery, DeliveryStatus, MealSkip, SubscriptionPause
from apps.deliveries.services import DeliverySelector, DeliveryService
from apps.meals.models import Meal
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription
from common.constants import Role, SubStatus

TODAY = datetime.date.today()


@pytest.fixture()
def biz_a(db):
    return Business.objects.create(name="Mess A")


@pytest.fixture()
def biz_b(db):
    return Business.objects.create(name="Mess B")


@pytest.fixture()
def owner_a(biz_a):
    return User.objects.create_user(username="owner_a", password="pass", role=Role.OWNER, business=biz_a)


@pytest.fixture()
def delivery_staff_a(biz_a):
    return User.objects.create_user(
        username="delivery_a", password="pass", role=Role.DELIVERY_STAFF, business=biz_a
    )


@pytest.fixture()
def kitchen_a(biz_a):
    return User.objects.create_user(
        username="kitchen_a", password="pass", role=Role.KITCHEN_STAFF, business=biz_a
    )


@pytest.fixture()
def owner_b(biz_b):
    return User.objects.create_user(username="owner_b", password="pass", role=Role.OWNER, business=biz_b)


@pytest.fixture()
def meal_a(biz_a):
    return Meal.objects.create(business=biz_a, name="Lunch")


@pytest.fixture()
def plan_a(biz_a, meal_a):
    return Plan.objects.create(
        business=biz_a, name="Weekly", meal=meal_a, duration_days=7, total_meals=7, price=Decimal("500.00")
    )


@pytest.fixture()
def cust_a(biz_a):
    return Customer.objects.create(business=biz_a, name="Alice", phone="1111111111")


@pytest.fixture()
def active_sub(biz_a, cust_a, plan_a):
    sub = Subscription.objects.create(
        business=biz_a,
        customer=cust_a,
        plan=plan_a,
        start_date=TODAY,
        end_date=TODAY + timedelta(days=7),
        status=SubStatus.ACTIVE,
        total_amount=Decimal("500.00"),
        paid_amount=Decimal("500.00"),
        pending_amount=Decimal("0.00"),
        remaining_meals=7,
    )
    return sub


@pytest.fixture()
def deliveries(active_sub):
    """Generate delivery schedule for active_sub."""
    DeliveryService.generate_delivery_schedule(active_sub)
    return Delivery.objects.filter(subscription=active_sub)


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


URL = "/api/v1/deliveries/"


# ── Schedule generation (D-03) ───────────────────────────────────────────


@pytest.mark.django_db
class TestDeliveryScheduleGeneration:
    def test_generates_correct_count(self, active_sub):
        created = DeliveryService.generate_delivery_schedule(active_sub)
        assert len(created) == 7

    def test_all_pending(self, deliveries):
        assert all(d.status == DeliveryStatus.PENDING for d in deliveries)

    def test_correct_date_range(self, deliveries, active_sub):
        dates = sorted(deliveries.values_list("delivery_date", flat=True))
        assert dates[0] == active_sub.start_date
        assert dates[-1] == active_sub.start_date + timedelta(days=6)

    def test_idempotent(self, active_sub):
        DeliveryService.generate_delivery_schedule(active_sub)
        DeliveryService.generate_delivery_schedule(active_sub)
        assert Delivery.objects.filter(subscription=active_sub).count() == 7


# ── Status transitions (D-05) ────────────────────────────────────────────


@pytest.mark.django_db
class TestDeliveryStatusTransitions:
    def test_pending_to_delivered(self, deliveries):
        d = deliveries.first()
        DeliveryService.update_status(d, DeliveryStatus.DELIVERED)
        d.refresh_from_db()
        assert d.status == DeliveryStatus.DELIVERED
        assert d.delivered_at is not None

    def test_pending_to_out_for_delivery(self, deliveries):
        d = deliveries.first()
        DeliveryService.update_status(d, DeliveryStatus.OUT_FOR_DELIVERY)
        assert d.status == DeliveryStatus.OUT_FOR_DELIVERY

    def test_out_to_delivered(self, deliveries):
        d = deliveries.first()
        DeliveryService.update_status(d, DeliveryStatus.OUT_FOR_DELIVERY)
        DeliveryService.update_status(d, DeliveryStatus.DELIVERED)
        assert d.status == DeliveryStatus.DELIVERED

    def test_delivered_is_terminal(self, deliveries):
        d = deliveries.first()
        DeliveryService.update_status(d, DeliveryStatus.DELIVERED)
        with pytest.raises(ValueError, match="Cannot transition"):
            DeliveryService.update_status(d, DeliveryStatus.PENDING)

    def test_status_update_with_notes(self, deliveries):
        d = deliveries.first()
        DeliveryService.update_status(d, DeliveryStatus.NOT_DELIVERED, notes="Customer not home")
        d.refresh_from_db()
        assert d.notes == "Customer not home"


# ── Skip meal (D-08) ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestMealSkip:
    def test_skip_creates_record(self, deliveries):
        d = deliveries.filter(delivery_date=TODAY + timedelta(days=1)).first()
        skip = DeliveryService.skip_meal(d, reason="Not hungry")
        assert skip.skip_date == d.delivery_date
        assert skip.reason == "Not hungry"
        d.refresh_from_db()
        assert d.status == DeliveryStatus.SKIPPED

    def test_cannot_skip_delivered(self, deliveries):
        d = deliveries.first()
        DeliveryService.update_status(d, DeliveryStatus.DELIVERED)
        with pytest.raises(ValueError, match="PENDING"):
            DeliveryService.skip_meal(d)

    def test_skip_record_count(self, deliveries):
        d = deliveries.first()
        DeliveryService.skip_meal(d)
        assert MealSkip.objects.count() == 1


# ── Pause/Resume deliveries (D-10) ───────────────────────────────────────


@pytest.mark.django_db
class TestPauseResumeDeliveries:
    def test_pause_cancels_deliveries_in_range(self, active_sub, deliveries):
        pause_start = TODAY + timedelta(days=2)
        pause_end = TODAY + timedelta(days=4)
        pause = DeliveryService.pause_deliveries(
            active_sub, start_date=pause_start, end_date=pause_end, reason="Holiday"
        )
        assert isinstance(pause, SubscriptionPause)
        cancelled = Delivery.objects.filter(
            subscription=active_sub,
            delivery_date__gte=pause_start,
            delivery_date__lte=pause_end,
            status=DeliveryStatus.CANCELLED,
        )
        assert cancelled.count() == 3

    def test_resume_restores_pending(self, active_sub, deliveries):
        pause_start = TODAY + timedelta(days=2)
        pause_end = TODAY + timedelta(days=4)
        pause = DeliveryService.pause_deliveries(active_sub, start_date=pause_start, end_date=pause_end)
        DeliveryService.resume_deliveries(active_sub, pause)
        restored = Delivery.objects.filter(
            subscription=active_sub,
            delivery_date__gte=pause_start,
            delivery_date__lte=pause_end,
            status=DeliveryStatus.PENDING,
        )
        assert restored.count() == 3

    def test_pause_record_created(self, active_sub, deliveries):
        DeliveryService.pause_deliveries(
            active_sub, start_date=TODAY + timedelta(days=1), end_date=TODAY + timedelta(days=2)
        )
        assert SubscriptionPause.objects.count() == 1


# ── Today's deliveries (D-04) ────────────────────────────────────────────


@pytest.mark.django_db
class TestTodayDeliveries:
    def test_get_today(self, active_sub, deliveries, biz_a):
        today_qs = DeliverySelector.get_today(biz_a.id)
        assert today_qs.count() == 1
        assert today_qs.first().delivery_date == TODAY


# ── Kitchen counts (D-11) ────────────────────────────────────────────────


@pytest.mark.django_db
class TestKitchenCounts:
    def test_counts(self, active_sub, deliveries, biz_a):
        counts = list(DeliverySelector.get_kitchen_counts(biz_a.id))
        assert len(counts) == 1
        assert counts[0]["meal__name"] == "Lunch"
        assert counts[0]["count"] == 1  # 1 delivery today


# ── Nightly expiry sweep (D-14) ──────────────────────────────────────────


@pytest.mark.django_db
class TestExpirySweep:
    def test_expire_past_subscriptions(self, biz_a, cust_a, plan_a):
        Subscription.objects.create(
            business=biz_a,
            customer=cust_a,
            plan=plan_a,
            start_date=TODAY - timedelta(days=35),
            end_date=TODAY - timedelta(days=5),
            status=SubStatus.ACTIVE,
            total_amount=Decimal("500"),
            paid_amount=Decimal("500"),
            pending_amount=Decimal("0"),
            remaining_meals=0,
        )
        count = DeliverySelector.expire_subscriptions()
        assert count == 1

    def test_does_not_expire_future(self, active_sub):
        count = DeliverySelector.expire_subscriptions()
        assert count == 0


# ── API endpoints ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDeliveryAPI:
    def test_list(self, owner_a, deliveries):
        resp = auth_client(owner_a).get(URL)
        assert resp.status_code == 200
        assert resp.json()["count"] == 7

    def test_today_endpoint(self, owner_a, deliveries):
        resp = auth_client(owner_a).get(f"{URL}today/")
        assert resp.status_code == 200

    def test_kitchen_counts_endpoint(self, kitchen_a, deliveries):
        resp = auth_client(kitchen_a).get(f"{URL}kitchen_counts/")
        assert resp.status_code == 200

    def test_status_update_via_api(self, owner_a, deliveries):
        d = deliveries.first()
        resp = auth_client(owner_a).patch(f"{URL}{d.id}/status/", {"status": "DELIVERED"}, format="json")
        assert resp.status_code == 200
        assert resp.json()["status"] == "DELIVERED"

    def test_skip_via_api(self, owner_a, deliveries):
        d = deliveries.filter(delivery_date=TODAY + timedelta(days=1)).first()
        resp = auth_client(owner_a).post(f"{URL}{d.id}/skip/", {"reason": "Holiday"}, format="json")
        assert resp.status_code == 200

    def test_delivery_staff_can_view(self, delivery_staff_a, deliveries):
        resp = auth_client(delivery_staff_a).get(URL)
        assert resp.status_code == 200

    def test_illegal_transition_returns_400(self, owner_a, deliveries):
        d = deliveries.first()
        DeliveryService.update_status(d, DeliveryStatus.DELIVERED)
        resp = auth_client(owner_a).patch(f"{URL}{d.id}/status/", {"status": "PENDING"}, format="json")
        assert resp.status_code == 400


# ── Tenant isolation ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDeliveryIsolation:
    def test_owner_b_cannot_see_biz_a_deliveries(self, owner_b, deliveries):
        resp = auth_client(owner_b).get(URL)
        assert resp.json()["count"] == 0

    def test_owner_b_gets_404_on_biz_a_delivery(self, owner_b, deliveries):
        d = deliveries.first()
        resp = auth_client(owner_b).patch(f"{URL}{d.id}/status/", {"status": "DELIVERED"}, format="json")
        assert resp.status_code == 404
