# ruff: noqa: F811 — fixtures imported from test_portal are injected by name
"""Regression tests for the medium-severity audit fixes (M1–M8).

M1 late payment shifts dates · M2 plan snapshot · M3 customer deactivation ·
M4 portal needs an ACTIVE customer · M5 customers kept off staff APIs ·
M6 staff quota · M7 same-day cut-off · M8 free plans.
"""

import datetime
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.deliveries.models import Delivery, DeliveryStatus
from apps.meals.models import Meal
from apps.payments.models import PaymentMethod
from apps.payments.services import PaymentService
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription
from apps.subscriptions.services import SubscriptionService
from apps.subscriptions.tests.test_portal import (  # noqa: F401 — pytest fixtures
    _set_cutoff,
    biz_a,
    client_for,
    cust_user_a,
    customer_a,
    meal_a,
    owner_a,
    plan_a,
    sub_a,
)
from common.constants import Role, Status, SubStatus

TODAY = datetime.date.today()


def _pay_in_full(sub):
    return PaymentService.record_payment(
        business_id=sub.business_id,
        subscription=sub,
        amount=sub.total_amount,
        method=PaymentMethod.CASH,
        payment_date=TODAY,
    )


def _new_sub(biz, customer, plan, start=TODAY):
    return SubscriptionService.create_subscription(
        business_id=biz.id, customer=customer, plan=plan, start_date=start
    )


# ── M1: paying late doesn't throw away the paid-for days ──────────────────


@pytest.mark.django_db
class TestLatePaymentShiftsDates:
    def test_paid_after_start_starts_today(self, biz_a, customer_a, plan_a):
        sub = _new_sub(biz_a, customer_a, plan_a)
        length = sub.end_date - sub.start_date
        # Created 5 days ago for that same day, unpaid until now.
        five_ago = TODAY - timedelta(days=5)
        Subscription.objects.filter(pk=sub.pk).update(
            start_date=five_ago, end_date=five_ago + length, created_at=timezone.now() - timedelta(days=5)
        )
        sub.refresh_from_db()
        _pay_in_full(sub)
        sub.refresh_from_db()
        assert sub.status == SubStatus.ACTIVE
        assert (sub.start_date, sub.end_date) == (TODAY, TODAY + length)
        assert not Delivery.objects.filter(subscription=sub, delivery_date__lt=TODAY).exists()

    def test_paid_after_end_date_still_gets_every_meal(self, biz_a, customer_a, plan_a):
        sub = _new_sub(biz_a, customer_a, plan_a)
        length = sub.end_date - sub.start_date
        forty_ago = TODAY - timedelta(days=40)
        Subscription.objects.filter(pk=sub.pk).update(
            start_date=forty_ago, end_date=forty_ago + length, created_at=timezone.now() - timedelta(days=40)
        )
        sub.refresh_from_db()
        _pay_in_full(sub)
        assert (
            Delivery.objects.filter(subscription=sub, delivery_date__gte=TODAY).count() == plan_a.total_meals
        )

    def test_backdated_subscription_keeps_owner_dates(self, biz_a, customer_a, plan_a):
        """Owner moving an existing customer in: entered today, started 10 days ago."""
        start = TODAY - timedelta(days=10)
        sub = _new_sub(biz_a, customer_a, plan_a, start=start)
        _pay_in_full(sub)
        sub.refresh_from_db()
        assert sub.start_date == start


# ── M2: editing a plan doesn't change subscriptions already sold ──────────


@pytest.mark.django_db
class TestPlanSnapshot:
    def test_subscription_copies_meal_and_count(self, biz_a, customer_a, plan_a):
        sub = _new_sub(biz_a, customer_a, plan_a)
        assert (sub.meal_id, sub.total_meals) == (plan_a.meal_id, 30)

    def test_plan_edit_after_sale_does_not_change_deliveries(self, biz_a, customer_a, plan_a, meal_a):
        sub = _new_sub(biz_a, customer_a, plan_a)
        dinner = Meal.objects.create(business=biz_a, name="Dinner")
        plan_a.total_meals = 20
        plan_a.meal = dinner
        plan_a.save()
        _pay_in_full(sub)
        deliveries = Delivery.objects.filter(subscription=sub)
        assert deliveries.count() == 30
        assert set(deliveries.values_list("meal_id", flat=True)) == {meal_a.id}

    def test_renewal_uses_current_plan(self, biz_a, customer_a, plan_a):
        sub = _new_sub(biz_a, customer_a, plan_a)
        SubscriptionService.cancel(sub)
        plan_a.total_meals = 26
        plan_a.save()
        renewal = SubscriptionService.renew(sub, start_date=sub.end_date + timedelta(days=1))
        assert renewal.total_meals == 26


# ── M3: removing a customer ───────────────────────────────────────────────

CUSTOMERS = "/api/v1/customers/"


@pytest.mark.django_db
class TestCustomerDeactivation:
    def test_cannot_delete_customer_with_live_subscription(self, owner_a, customer_a, sub_a):
        resp = client_for(owner_a).delete(f"{CUSTOMERS}{customer_a.id}/")
        assert resp.status_code == 400
        assert "Cancel it first" in str(resp.json())
        customer_a.refresh_from_db()
        assert customer_a.status == Status.ACTIVE

    def test_cannot_patch_to_inactive_with_live_subscription(self, owner_a, customer_a, sub_a):
        resp = client_for(owner_a).patch(
            f"{CUSTOMERS}{customer_a.id}/", {"status": "INACTIVE"}, format="json"
        )
        assert resp.status_code == 400

    def test_delete_after_cancelling(self, owner_a, customer_a, sub_a, cust_user_a):
        SubscriptionService.cancel(sub_a)
        assert client_for(owner_a).delete(f"{CUSTOMERS}{customer_a.id}/").status_code == 204
        cust_user_a.refresh_from_db()
        assert cust_user_a.is_active is False

    @pytest.mark.parametrize("status", [Status.BLOCKED, Status.INACTIVE])
    def test_no_new_subscription_for_non_active_customer(self, biz_a, customer_a, plan_a, status):
        Customer.objects.filter(pk=customer_a.pk).update(status=status)
        customer_a.refresh_from_db()
        with pytest.raises(ValueError, match="Make them active first"):
            _new_sub(biz_a, customer_a, plan_a)

    def test_no_new_subscription_via_api(self, owner_a, customer_a, plan_a):
        Customer.objects.filter(pk=customer_a.pk).update(status=Status.BLOCKED)
        resp = client_for(owner_a).post(
            "/api/v1/subscriptions/",
            {"customer": str(customer_a.id), "plan": str(plan_a.id), "start_date": str(TODAY)},
            format="json",
        )
        assert resp.status_code == 400


# ── M4: portal only for ACTIVE customers ──────────────────────────────────


@pytest.mark.django_db
class TestPortalNeedsActiveCustomer:
    def test_blocked_customer_loses_portal(self, owner_a, customer_a, cust_user_a, sub_a):
        resp = client_for(owner_a).patch(f"{CUSTOMERS}{customer_a.id}/", {"status": "BLOCKED"}, format="json")
        assert resp.status_code == 200
        cust_user_a.refresh_from_db()
        assert cust_user_a.is_active is False  # login switched off with the status

    def test_portal_refuses_blocked_customer_even_with_login_on(self, customer_a, cust_user_a, sub_a):
        Customer.objects.filter(pk=customer_a.pk).update(status=Status.BLOCKED)
        resp = client_for(cust_user_a).get("/api/v1/portal/dashboard/")
        assert resp.status_code == 403

    def test_cannot_enable_login_for_inactive_customer(self, owner_a, customer_a, cust_user_a):
        Customer.objects.filter(pk=customer_a.pk).update(status=Status.INACTIVE)
        resp = client_for(owner_a).post(f"{CUSTOMERS}{customer_a.id}/portal-login/enable/")
        assert resp.status_code == 400


# ── M5: customers can't use the staff APIs ────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/subscriptions/",
        "/api/v1/payments/",
        "/api/v1/deliveries/",
        "/api/v1/plans/",
        "/api/v1/business/",
    ],
)
def test_customer_kept_off_staff_apis(cust_user_a, customer_a, sub_a, url):
    assert client_for(cust_user_a).get(url).status_code == 403


# ── M6: plan's staff limit ────────────────────────────────────────────────


@pytest.fixture()
def one_staff_plan(biz_a):
    from apps.platform.models import SaasPlan
    from apps.platform.services import PlatformService

    plan = SaasPlan.objects.create(name="Tiny", price_monthly=Decimal("100"), max_staff=1)
    sub = PlatformService.start_billing(biz_a, plan=plan)
    sub.status = "ACTIVE"
    sub.save(update_fields=["status"])
    return plan


def _staff_payload(n):
    return {
        "username": f"staff{n}",
        "password": "staffpass123",
        "name": f"Staff {n}",
        "role": Role.DELIVERY_STAFF,
    }


@pytest.mark.django_db
class TestStaffQuota:
    def test_second_staff_refused(self, owner_a, one_staff_plan):
        api = client_for(owner_a)
        assert api.post("/api/v1/staff/", _staff_payload(1), format="json").status_code == 201
        resp = api.post("/api/v1/staff/", _staff_payload(2), format="json")
        assert resp.status_code == 402

    def test_owner_and_customer_logins_dont_use_seats(self, owner_a, cust_user_a, customer_a, one_staff_plan):
        User.objects.create_user(
            username="owner2", password="pass", role=Role.OWNER, business=owner_a.business
        )
        resp = client_for(owner_a).post("/api/v1/staff/", _staff_payload(1), format="json")
        assert resp.status_code == 201

    def test_deactivated_staff_frees_seat_and_reactivating_is_checked(self, owner_a, one_staff_plan):
        api = client_for(owner_a)
        first = api.post("/api/v1/staff/", _staff_payload(1), format="json").json()["id"]
        api.post(f"/api/v1/staff/{first}/deactivate/")
        assert api.post("/api/v1/staff/", _staff_payload(2), format="json").status_code == 201
        assert api.post(f"/api/v1/staff/{first}/activate/").status_code == 402
        resp = api.patch(f"/api/v1/staff/{first}/", {"is_active": True}, format="json")
        assert resp.status_code == 402


# ── M7: customers can't change today's meal once cooking starts ───────────


@pytest.fixture()
def two_deliveries(sub_a):
    return [
        Delivery.objects.create(
            business=sub_a.business,
            subscription=sub_a,
            customer=sub_a.customer,
            meal=sub_a.plan.meal,
            delivery_date=TODAY + timedelta(days=i),
            status=DeliveryStatus.PENDING,
        )
        for i in (0, 1)
    ]


def _skip(user, sub, date=None):
    body = {"date": str(date)} if date else {}
    return client_for(user).post(f"/api/v1/portal/subscriptions/{sub.id}/skip/", body, format="json")


@pytest.mark.django_db
class TestSameDayCutoff:
    def test_today_locked_after_cutoff(self, cust_user_a, sub_a, two_deliveries):
        _set_cutoff(sub_a.business, datetime.time.min)
        resp = _skip(cust_user_a, sub_a, TODAY)
        assert resp.status_code == 400
        assert "Today's meal can't be changed" in resp.json()["error"]["message"]

    def test_today_locked_when_no_cutoff_set(self, cust_user_a, sub_a, two_deliveries):
        assert _skip(cust_user_a, sub_a, TODAY).status_code == 400

    def test_skip_without_date_after_cutoff_takes_tomorrow(self, cust_user_a, sub_a, two_deliveries):
        today, tomorrow = two_deliveries
        assert _skip(cust_user_a, sub_a).status_code == 200
        today.refresh_from_db()
        tomorrow.refresh_from_db()
        assert (today.status, tomorrow.status) == (DeliveryStatus.PENDING, DeliveryStatus.SKIPPED)

    def test_pause_from_today_locked_after_cutoff(self, cust_user_a, sub_a):
        _set_cutoff(sub_a.business, datetime.time.min)
        resp = client_for(cust_user_a).post(
            f"/api/v1/portal/subscriptions/{sub_a.id}/pause-request/",
            {"start_date": str(TODAY), "end_date": str(TODAY + timedelta(days=1))},
            format="json",
        )
        assert resp.status_code == 400

    def test_owner_can_still_skip_today(self, owner_a, sub_a, two_deliveries):
        today = two_deliveries[0]
        assert client_for(owner_a).post(f"/api/v1/deliveries/{today.id}/skip/").status_code == 200


# ── M8: free plans ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestFreePlan:
    def test_free_plan_activates_on_creation(self, biz_a, customer_a, meal_a):
        free = Plan.objects.create(
            business=biz_a, name="Free tasting week", meal=meal_a, duration_days=7, total_meals=7, price=0
        )
        sub = _new_sub(biz_a, customer_a, free)
        assert sub.status == SubStatus.ACTIVE
        assert Delivery.objects.filter(subscription=sub).count() == 7

    def test_paid_plan_still_starts_pending(self, biz_a, customer_a, plan_a):
        assert _new_sub(biz_a, customer_a, plan_a).status == SubStatus.PENDING
