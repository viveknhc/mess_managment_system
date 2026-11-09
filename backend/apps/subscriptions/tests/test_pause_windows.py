"""Pause windows: owner/portal pause, resume, daily sweep, end-date extension,
illegal transitions, tenant isolation (D-10)."""

import datetime
from datetime import timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.deliveries.models import Delivery, DeliveryStatus, SubscriptionPause
from apps.deliveries.services import DeliverySelector, DeliveryService
from apps.meals.models import Meal
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription
from apps.subscriptions.services import PauseValidationError, SubscriptionService
from apps.subscriptions.tasks import process_pause_windows_task
from common.constants import Role, SubStatus

T = datetime.date.today()


def d(n):
    return T + timedelta(days=n)


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
def staff_a(biz_a):
    return User.objects.create_user(
        username="staff_a", password="pass", role=Role.DELIVERY_STAFF, business=biz_a
    )


@pytest.fixture()
def owner_b(biz_b):
    return User.objects.create_user(username="owner_b", password="pass", role=Role.OWNER, business=biz_b)


@pytest.fixture()
def cust_user_a(biz_a):
    return User.objects.create_user(username="cust_a", password="pass", role=Role.CUSTOMER, business=biz_a)


@pytest.fixture()
def plan_a(biz_a):
    meal = Meal.objects.create(business=biz_a, name="Lunch")
    return Plan.objects.create(
        business=biz_a,
        name="Weekly",
        meal=meal,
        duration_days=7,
        total_meals=7,
        price=Decimal("700.00"),
        pause_allowed=True,
    )


@pytest.fixture()
def cust_a(biz_a, cust_user_a):
    return Customer.objects.create(business=biz_a, user=cust_user_a, name="Alice", phone="1111111111")


def make_sub(biz, cust, plan, status=SubStatus.ACTIVE):
    return Subscription.objects.create(
        business=biz,
        customer=cust,
        plan=plan,
        start_date=T,
        end_date=d(7),
        status=status,
        total_amount=Decimal("700.00"),
        paid_amount=Decimal("700.00"),
        pending_amount=Decimal("0.00"),
        remaining_meals=7,
    )


@pytest.fixture()
def sub(biz_a, cust_a, plan_a):
    s = make_sub(biz_a, cust_a, plan_a)
    DeliveryService.generate_delivery_schedule(s)  # deliveries T .. T+6
    return s


def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def url(sub_id, action):
    return f"/api/v1/subscriptions/{sub_id}/{action}/"


def status_on(sub, n):
    return Delivery.objects.get(subscription=sub, delivery_date=d(n)).status


def pending_dates(sub):
    return sorted(
        Delivery.objects.filter(subscription=sub, status=DeliveryStatus.PENDING).values_list(
            "delivery_date", flat=True
        )
    )


# ── Owner pause / resume ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestOwnerPause:
    def test_pause_removes_delivery_from_today_list(self, owner_a, staff_a, sub, biz_a):
        before = client(staff_a).get("/api/v1/deliveries/today/").json()
        assert before["count"] == 1

        resp = client(owner_a).post(url(sub.id, "pause"))
        assert resp.status_code == 200
        assert resp.json()["status"] == SubStatus.PAUSED

        after = client(staff_a).get("/api/v1/deliveries/today/").json()
        assert after["count"] == 0
        assert DeliverySelector.get_today_summary(biz_a.id)["total"] == 0
        # Open-ended: every future delivery cancelled
        assert pending_dates(sub) == []
        pause = SubscriptionPause.objects.get(subscription=sub)
        assert pause.start_date == T and pause.end_date is None

    def test_resume_restores_deliveries(self, owner_a, staff_a, sub):
        client(owner_a).post(url(sub.id, "pause"))
        resp = client(owner_a).post(url(sub.id, "resume"))
        assert resp.status_code == 200
        assert resp.json()["status"] == SubStatus.ACTIVE

        assert client(staff_a).get("/api/v1/deliveries/today/").json()["count"] == 1
        assert pending_dates(sub) == [d(i) for i in range(7)]
        sub.refresh_from_db()
        assert sub.end_date == d(7)  # resumed same day — nothing paused, no extension
        pause = SubscriptionPause.objects.get(subscription=sub)
        assert pause.is_closed and pause.days_extended == 0

    def test_resume_after_two_days_extends_end_date(self, sub):
        SubscriptionService.pause(sub)
        SubscriptionService.resume(sub, today=d(2))
        sub.refresh_from_db()

        assert sub.status == SubStatus.ACTIVE
        assert status_on(sub, 0) == DeliveryStatus.CANCELLED
        assert status_on(sub, 1) == DeliveryStatus.CANCELLED
        # 2 paused meals → end_date +2, two replacement deliveries after the schedule
        assert sub.end_date == d(9)
        assert pending_dates(sub) == [d(i) for i in range(2, 9)]
        assert SubscriptionPause.objects.get(subscription=sub).days_extended == 2

    def test_owner_future_window_via_api(self, owner_a, sub):
        resp = client(owner_a).post(
            url(sub.id, "pause"),
            {"start_date": str(d(3)), "end_date": str(d(4)), "reason": "Holiday"},
            format="json",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == SubStatus.ACTIVE
        assert body["pauses"][0]["start_date"] == str(d(3))
        assert status_on(sub, 3) == DeliveryStatus.CANCELLED
        assert status_on(sub, 0) == DeliveryStatus.PENDING

    def test_pause_does_not_touch_non_pending(self, sub):
        today = Delivery.objects.get(subscription=sub, delivery_date=T)
        DeliveryService.update_status(today, DeliveryStatus.DELIVERED)
        SubscriptionService.pause(sub)
        assert status_on(sub, 0) == DeliveryStatus.DELIVERED


# ── Portal pause + daily sweep ───────────────────────────────────────────


@pytest.mark.django_db
class TestPauseWindowSweep:
    def test_future_portal_pause_flips_on_start_and_end(self, cust_user_a, sub):
        resp = client(cust_user_a).post(
            f"/api/v1/portal/subscriptions/{sub.id}/pause-request/",
            {"start_date": str(d(2)), "end_date": str(d(4))},
            format="json",
        )
        assert resp.status_code == 200
        sub.refresh_from_db()
        assert sub.status == SubStatus.ACTIVE  # future window
        assert [status_on(sub, i) for i in (2, 3, 4)] == [DeliveryStatus.CANCELLED] * 3
        assert status_on(sub, 1) == DeliveryStatus.PENDING

        assert SubscriptionService.process_pause_windows(today=d(1)) == {"started": 0, "ended": 0}
        sub.refresh_from_db()
        assert sub.status == SubStatus.ACTIVE

        assert SubscriptionService.process_pause_windows(today=d(2)) == {"started": 1, "ended": 0}
        sub.refresh_from_db()
        assert sub.status == SubStatus.PAUSED

        SubscriptionService.process_pause_windows(today=d(4))
        sub.refresh_from_db()
        assert sub.status == SubStatus.PAUSED

        assert SubscriptionService.process_pause_windows(today=d(5)) == {"started": 0, "ended": 1}
        sub.refresh_from_db()
        assert sub.status == SubStatus.ACTIVE
        assert sub.end_date == d(10)  # 3 paused meals
        assert pending_dates(sub) == [d(0), d(1), d(5), d(6), d(7), d(8), d(9)]

        # Idempotent
        assert SubscriptionService.process_pause_windows(today=d(5)) == {"started": 0, "ended": 0}
        sub.refresh_from_db()
        assert sub.end_date == d(10)
        assert Delivery.objects.filter(subscription=sub).count() == 10

    def test_window_past_end_date_extends_from_window_end(self, sub):
        SubscriptionService.pause(sub, start_date=d(5), end_date=d(12))
        SubscriptionService.process_pause_windows(today=d(5))
        sub.refresh_from_db()
        assert sub.status == SubStatus.PAUSED
        # Paused subs are not expired by the nightly sweep
        assert DeliverySelector.expire_subscriptions() == 0

        SubscriptionService.process_pause_windows(today=d(13))
        sub.refresh_from_db()
        assert sub.status == SubStatus.ACTIVE
        assert sub.end_date == d(14)  # max(end, last paused day) + 2 paused meals
        assert pending_dates(sub) == [d(i) for i in range(5)] + [d(13), d(14)]

    def test_manual_resume_keeps_future_window(self, sub):
        SubscriptionService.pause(sub, start_date=d(4), end_date=d(5))  # scheduled while ACTIVE
        SubscriptionService.pause(sub, end_date=d(1))  # starts today → PAUSED
        SubscriptionService.resume(sub, today=d(1))
        sub.refresh_from_db()
        assert sub.status == SubStatus.ACTIVE
        assert status_on(sub, 1) == DeliveryStatus.PENDING
        assert status_on(sub, 4) == DeliveryStatus.CANCELLED  # scheduled window untouched
        SubscriptionService.process_pause_windows(today=d(4))
        sub.refresh_from_db()
        assert sub.status == SubStatus.PAUSED

    def test_celery_task_runs(self, sub):
        SubscriptionService.pause(sub, start_date=d(1), end_date=d(1))
        assert process_pause_windows_task() == {"started": 0, "ended": 0}


# ── Illegal transitions / validation ─────────────────────────────────────


@pytest.mark.django_db
class TestPauseIllegal:
    @pytest.mark.parametrize("status", [SubStatus.PENDING, SubStatus.CANCELLED, SubStatus.EXPIRED])
    def test_cannot_pause_non_active(self, owner_a, biz_a, cust_a, plan_a, status):
        s = make_sub(biz_a, cust_a, plan_a, status=status)
        with pytest.raises(ValueError, match="Cannot transition"):
            SubscriptionService.pause(s)
        resp = client(owner_a).post(url(s.id, "pause"))
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_TRANSITION"
        assert not SubscriptionPause.objects.filter(subscription=s).exists()

    def test_cannot_pause_twice(self, owner_a, sub):
        SubscriptionService.pause(sub)
        resp = client(owner_a).post(url(sub.id, "pause"))
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_TRANSITION"

    @pytest.mark.parametrize("status", [SubStatus.ACTIVE, SubStatus.PENDING, SubStatus.CANCELLED])
    def test_cannot_resume_non_paused(self, owner_a, biz_a, cust_a, plan_a, status):
        s = make_sub(biz_a, cust_a, plan_a, status=status)
        resp = client(owner_a).post(url(s.id, "resume"))
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_TRANSITION"

    def test_resume_with_only_future_window_is_illegal(self, sub):
        SubscriptionService.pause(sub, start_date=d(3), end_date=d(4))
        with pytest.raises(ValueError, match="Cannot resume"):
            SubscriptionService.resume(sub)

    def test_overlapping_window_rejected(self, sub):
        SubscriptionService.pause(sub, start_date=d(2), end_date=d(4))
        with pytest.raises(PauseValidationError, match="overlaps"):
            SubscriptionService.pause(sub, start_date=d(4), end_date=d(6))

    @pytest.mark.parametrize(
        "body",
        [
            {"start_date": str(d(-1))},
            {"start_date": str(d(3)), "end_date": str(d(2))},
            {"start_date": str(d(30))},
        ],
    )
    def test_bad_dates_rejected(self, owner_a, sub, body):
        resp = client(owner_a).post(url(sub.id, "pause"), body, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
        sub.refresh_from_db()
        assert sub.status == SubStatus.ACTIVE


# ── Tenant isolation ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPauseIsolation:
    def test_other_business_cannot_pause(self, owner_b, sub):
        resp = client(owner_b).post(
            url(sub.id, "pause"), {"start_date": str(d(1)), "end_date": str(d(2))}, format="json"
        )
        assert resp.status_code == 404
        assert not SubscriptionPause.objects.filter(subscription=sub).exists()
        assert status_on(sub, 1) == DeliveryStatus.PENDING

    def test_other_business_cannot_resume(self, owner_b, sub):
        SubscriptionService.pause(sub)
        resp = client(owner_b).post(url(sub.id, "resume"))
        assert resp.status_code == 404
        sub.refresh_from_db()
        assert sub.status == SubStatus.PAUSED
