"""Subscription state machine, CRUD, isolation tests (S-10)."""

import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.meals.models import Meal
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription
from apps.subscriptions.services import SubscriptionSelector, SubscriptionService
from common.constants import Role, SubStatus


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
def manager_a(biz_a):
    return User.objects.create_user(username="manager_a", password="pass", role=Role.MANAGER, business=biz_a)


@pytest.fixture()
def delivery_a(biz_a):
    return User.objects.create_user(
        username="delivery_a", password="pass", role=Role.DELIVERY_STAFF, business=biz_a
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
        business=biz_a,
        name="Monthly",
        meal=meal_a,
        duration_days=30,
        total_meals=30,
        price=Decimal("2500.00"),
    )


@pytest.fixture()
def cust_a(biz_a):
    return Customer.objects.create(business=biz_a, name="Alice", phone="1111111111")


@pytest.fixture()
def cust_b(biz_b):
    return Customer.objects.create(business=biz_b, name="Charlie")


@pytest.fixture()
def meal_b(biz_b):
    return Meal.objects.create(business=biz_b, name="Dinner")


@pytest.fixture()
def plan_b(biz_b, meal_b):
    return Plan.objects.create(
        business=biz_b, name="Weekly", meal=meal_b, duration_days=7, total_meals=7, price=Decimal("500.00")
    )


@pytest.fixture()
def sub_pending(biz_a, cust_a, plan_a):
    return Subscription.objects.create(
        business=biz_a,
        customer=cust_a,
        plan=plan_a,
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=30),
        status=SubStatus.PENDING,
        total_amount=Decimal("2500.00"),
        paid_amount=Decimal("0.00"),
        pending_amount=Decimal("2500.00"),
        remaining_meals=30,
    )


@pytest.fixture()
def sub_active(sub_pending):
    sub_pending.status = SubStatus.ACTIVE
    sub_pending.paid_amount = Decimal("2500.00")
    sub_pending.pending_amount = Decimal("0.00")
    sub_pending.save()
    return sub_pending


@pytest.fixture()
def sub_b(biz_b, cust_b, plan_b):
    return Subscription.objects.create(
        business=biz_b,
        customer=cust_b,
        plan=plan_b,
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=7),
        status=SubStatus.PENDING,
        total_amount=Decimal("500.00"),
        paid_amount=Decimal("0.00"),
        pending_amount=Decimal("500.00"),
        remaining_meals=7,
    )


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


URL = "/api/v1/subscriptions/"


def detail_url(pk):
    return f"{URL}{pk}/"


# ── Service: create ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCreateSubscription:
    def test_create_pending(self, biz_a, cust_a, plan_a):
        sub = SubscriptionService.create_subscription(
            business_id=biz_a.id, customer=cust_a, plan=plan_a, start_date=datetime.date.today()
        )
        assert sub.status == SubStatus.PENDING
        assert sub.total_amount == Decimal("2500.00")
        assert sub.pending_amount == Decimal("2500.00")
        assert sub.remaining_meals == 30
        assert sub.end_date == datetime.date.today() + datetime.timedelta(days=30)

    def test_cross_business_customer_rejected(self, biz_a, cust_b, plan_a):
        with pytest.raises(ValueError, match="Customer does not belong"):
            SubscriptionService.create_subscription(
                business_id=biz_a.id, customer=cust_b, plan=plan_a, start_date=datetime.date.today()
            )

    def test_cross_business_plan_rejected(self, biz_a, cust_a, plan_b):
        with pytest.raises(ValueError, match="Plan does not belong"):
            SubscriptionService.create_subscription(
                business_id=biz_a.id, customer=cust_a, plan=plan_b, start_date=datetime.date.today()
            )

    def test_inactive_plan_rejected(self, biz_a, cust_a, plan_a):
        plan_a.is_active = False
        plan_a.save()
        with pytest.raises(ValueError, match="inactive plan"):
            SubscriptionService.create_subscription(
                business_id=biz_a.id, customer=cust_a, plan=plan_a, start_date=datetime.date.today()
            )


# ── State machine: legal transitions ─────────────────────────────────────


@pytest.mark.django_db
class TestLegalTransitions:
    def test_pending_to_active(self, sub_pending):
        sub_pending.transition_to(SubStatus.ACTIVE)
        assert sub_pending.status == SubStatus.ACTIVE

    def test_pending_to_cancelled(self, sub_pending):
        sub_pending.transition_to(SubStatus.CANCELLED)
        assert sub_pending.status == SubStatus.CANCELLED

    def test_active_to_paused(self, sub_active):
        sub_active.transition_to(SubStatus.PAUSED)
        assert sub_active.status == SubStatus.PAUSED

    def test_active_to_cancelled(self, sub_active):
        sub_active.transition_to(SubStatus.CANCELLED)
        assert sub_active.status == SubStatus.CANCELLED

    def test_active_to_expired(self, sub_active):
        sub_active.transition_to(SubStatus.EXPIRED)
        assert sub_active.status == SubStatus.EXPIRED

    def test_paused_to_active(self, sub_active):
        sub_active.transition_to(SubStatus.PAUSED)
        sub_active.transition_to(SubStatus.ACTIVE)
        assert sub_active.status == SubStatus.ACTIVE


# ── State machine: illegal transitions ───────────────────────────────────


@pytest.mark.django_db
class TestIllegalTransitions:
    def test_pending_to_paused(self, sub_pending):
        with pytest.raises(ValueError, match="Cannot transition"):
            sub_pending.transition_to(SubStatus.PAUSED)

    def test_pending_to_expired(self, sub_pending):
        with pytest.raises(ValueError, match="Cannot transition"):
            sub_pending.transition_to(SubStatus.EXPIRED)

    def test_paused_to_cancelled(self, sub_active):
        sub_active.transition_to(SubStatus.PAUSED)
        with pytest.raises(ValueError, match="Cannot transition"):
            sub_active.transition_to(SubStatus.CANCELLED)

    def test_expired_to_active(self, sub_active):
        sub_active.transition_to(SubStatus.EXPIRED)
        with pytest.raises(ValueError, match="Cannot transition"):
            sub_active.transition_to(SubStatus.ACTIVE)

    def test_cancelled_to_active(self, sub_pending):
        sub_pending.transition_to(SubStatus.CANCELLED)
        with pytest.raises(ValueError, match="Cannot transition"):
            sub_pending.transition_to(SubStatus.ACTIVE)


# ── Service actions ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestServiceActions:
    def test_pause(self, sub_active):
        result = SubscriptionService.pause(sub_active)
        assert result.status == SubStatus.PAUSED

    def test_resume(self, sub_active):
        SubscriptionService.pause(sub_active)
        result = SubscriptionService.resume(sub_active)
        assert result.status == SubStatus.ACTIVE

    def test_cancel(self, sub_active):
        result = SubscriptionService.cancel(sub_active)
        assert result.status == SubStatus.CANCELLED

    def test_pause_pending_fails(self, sub_pending):
        with pytest.raises(ValueError):
            SubscriptionService.pause(sub_pending)

    def test_resume_active_fails(self, sub_active):
        with pytest.raises(ValueError):
            SubscriptionService.resume(sub_active)


# ── Renewal ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestRenewal:
    def test_renew_expired(self, sub_active, plan_a):
        sub_active.transition_to(SubStatus.EXPIRED)
        sub_active.save()
        new_sub = SubscriptionService.renew(sub_active)
        assert new_sub.status == SubStatus.PENDING
        assert new_sub.renewed_from_id == sub_active.id
        assert new_sub.total_amount == plan_a.price
        assert new_sub.remaining_meals == plan_a.total_meals

    def test_renew_cancelled(self, sub_pending):
        sub_pending.transition_to(SubStatus.CANCELLED)
        sub_pending.save()
        new_sub = SubscriptionService.renew(sub_pending)
        assert new_sub.renewed_from_id == sub_pending.id

    def test_renew_active_fails(self, sub_active):
        with pytest.raises(ValueError, match="EXPIRED or CANCELLED"):
            SubscriptionService.renew(sub_active)

    def test_renew_with_inactive_plan_fails(self, sub_active, plan_a):
        sub_active.transition_to(SubStatus.EXPIRED)
        sub_active.save()
        plan_a.is_active = False
        plan_a.save()
        with pytest.raises(ValueError, match="inactive plan"):
            SubscriptionService.renew(sub_active)


# ── Expiring selector ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestExpiringSelector:
    def test_expiring_within_3_days(self, biz_a, cust_a, plan_a):
        sub = Subscription.objects.create(
            business=biz_a,
            customer=cust_a,
            plan=plan_a,
            start_date=datetime.date.today() - datetime.timedelta(days=27),
            end_date=datetime.date.today() + datetime.timedelta(days=2),
            status=SubStatus.ACTIVE,
            total_amount=Decimal("2500.00"),
            paid_amount=Decimal("2500.00"),
            pending_amount=Decimal("0.00"),
            remaining_meals=3,
        )
        expiring = SubscriptionSelector.get_expiring(biz_a.id)
        assert sub in expiring
        assert sub.is_expiring is True

    def test_not_expiring_if_far(self, sub_active):
        expiring = SubscriptionSelector.get_expiring(sub_active.business_id)
        assert sub_active not in expiring
        assert sub_active.is_expiring is False

    def test_not_expiring_if_paused(self, biz_a, cust_a, plan_a):
        sub = Subscription.objects.create(
            business=biz_a,
            customer=cust_a,
            plan=plan_a,
            start_date=datetime.date.today() - datetime.timedelta(days=28),
            end_date=datetime.date.today() + datetime.timedelta(days=1),
            status=SubStatus.PAUSED,
            total_amount=Decimal("2500.00"),
            paid_amount=Decimal("2500.00"),
            pending_amount=Decimal("0.00"),
            remaining_meals=2,
        )
        expiring = SubscriptionSelector.get_expiring(biz_a.id)
        assert sub not in expiring


# ── Remaining days/meals ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestRemainingCalculations:
    def test_remaining_days(self, sub_active):
        assert sub_active.remaining_days == 30

    def test_remaining_days_past(self, sub_active):
        sub_active.end_date = datetime.date.today() - datetime.timedelta(days=5)
        assert sub_active.remaining_days == 0


# ── API endpoints ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSubscriptionAPI:
    def test_create_via_api(self, owner_a, cust_a, plan_a):
        resp = auth_client(owner_a).post(
            URL,
            {"customer": str(cust_a.id), "plan": str(plan_a.id), "start_date": str(datetime.date.today())},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == SubStatus.PENDING

    def test_list(self, owner_a, sub_pending):
        resp = auth_client(owner_a).get(URL)
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_retrieve(self, owner_a, sub_pending):
        resp = auth_client(owner_a).get(detail_url(sub_pending.id))
        assert resp.status_code == 200
        assert "remaining_days" in resp.json()
        assert "is_expiring" in resp.json()

    def test_filter_by_status(self, owner_a, sub_pending, sub_active):
        resp = auth_client(owner_a).get(URL, {"status": "ACTIVE"})
        assert resp.json()["count"] == 1

    def test_filter_by_customer(self, owner_a, sub_pending, cust_a):
        resp = auth_client(owner_a).get(URL, {"customer": str(cust_a.id)})
        assert resp.json()["count"] == 1

    def test_delivery_can_list(self, delivery_a, sub_pending):
        resp = auth_client(delivery_a).get(URL)
        assert resp.status_code == 200

    def test_delivery_cannot_create(self, delivery_a, cust_a, plan_a):
        resp = auth_client(delivery_a).post(
            URL,
            {"customer": str(cust_a.id), "plan": str(plan_a.id)},
            format="json",
        )
        assert resp.status_code == 403

    def test_pause_via_api(self, owner_a, sub_active):
        resp = auth_client(owner_a).post(f"{detail_url(sub_active.id)}pause/")
        assert resp.status_code == 200
        assert resp.json()["status"] == SubStatus.PAUSED

    def test_resume_via_api(self, owner_a, sub_active):
        SubscriptionService.pause(sub_active)
        resp = auth_client(owner_a).post(f"{detail_url(sub_active.id)}resume/")
        assert resp.status_code == 200
        assert resp.json()["status"] == SubStatus.ACTIVE

    def test_cancel_via_api(self, owner_a, sub_active):
        resp = auth_client(owner_a).post(f"{detail_url(sub_active.id)}cancel/")
        assert resp.status_code == 200
        assert resp.json()["status"] == SubStatus.CANCELLED

    def test_renew_via_api(self, owner_a, sub_active):
        sub_active.status = SubStatus.EXPIRED
        sub_active.save()
        resp = auth_client(owner_a).post(f"{detail_url(sub_active.id)}renew/")
        assert resp.status_code == 201
        assert resp.json()["status"] == SubStatus.PENDING
        assert resp.json()["renewed_from"] == str(sub_active.id)

    def test_illegal_transition_returns_400(self, owner_a, sub_pending):
        resp = auth_client(owner_a).post(f"{detail_url(sub_pending.id)}pause/")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_TRANSITION"

    def test_cross_business_customer_via_api(self, owner_a, cust_b, plan_a):
        resp = auth_client(owner_a).post(
            URL,
            {"customer": str(cust_b.id), "plan": str(plan_a.id)},
            format="json",
        )
        assert resp.status_code == 400


# ── Tenant isolation ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSubscriptionIsolation:
    def test_owner_b_cannot_see_biz_a_subs(self, owner_b, sub_pending):
        resp = auth_client(owner_b).get(URL)
        assert resp.json()["count"] == 0

    def test_owner_b_gets_404_on_biz_a_sub(self, owner_b, sub_pending):
        resp = auth_client(owner_b).get(detail_url(sub_pending.id))
        assert resp.status_code == 404

    def test_owner_b_cannot_pause_biz_a_sub(self, owner_b, sub_active):
        resp = auth_client(owner_b).post(f"{detail_url(sub_active.id)}pause/")
        assert resp.status_code == 404

    def test_both_see_only_own(self, owner_a, owner_b, sub_pending, sub_b):
        resp_a = auth_client(owner_a).get(URL)
        resp_b = auth_client(owner_b).get(URL)
        ids_a = {r["id"] for r in resp_a.json()["results"]}
        ids_b = {r["id"] for r in resp_b.json()["results"]}
        assert ids_a.isdisjoint(ids_b)
