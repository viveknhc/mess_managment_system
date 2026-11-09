"""Platform billing module tests — monthly plan terms, quota, suspension, SUPER_ADMIN isolation."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.platform.models import SaasPayment, SaasPlan, SaasStatus
from apps.platform.services import PlatformService, add_months
from common.constants import Role, Status

# ── Fixtures ──────────────────────────────────────────────────────────────


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
def owner_b(biz_b):
    return User.objects.create_user(username="owner_b", password="pass", role=Role.OWNER, business=biz_b)


@pytest.fixture()
def super_admin(db):
    return User.objects.create_user(username="super", password="pass", role=Role.SUPER_ADMIN)


@pytest.fixture()
def plan_basic(db):
    return SaasPlan.objects.create(
        name="Basic",
        price_monthly=Decimal("499.00"),
        max_customers=50,
        max_staff=3,
        features=["50 customers", "3 staff", "Email support"],
        is_active=True,
    )


@pytest.fixture()
def plan_pro(db):
    return SaasPlan.objects.create(
        name="Pro",
        price_monthly=Decimal("999.00"),
        max_customers=0,
        max_staff=0,
        features=["Unlimited customers", "Unlimited staff", "Priority support"],
        is_active=True,
    )


@pytest.fixture()
def sub_a(biz_a):
    return PlatformService.start_billing(biz_a)


@pytest.fixture()
def manager_a(biz_a):
    return User.objects.create_user(username="manager_a", password="pass", role=Role.MANAGER, business=biz_a)


@pytest.fixture()
def client_a(owner_a):
    c = APIClient()
    c.force_authenticate(user=owner_a)
    return c


@pytest.fixture()
def client_b(owner_b):
    c = APIClient()
    c.force_authenticate(user=owner_b)
    return c


@pytest.fixture()
def client_super(super_admin):
    c = APIClient()
    c.force_authenticate(user=super_admin)
    return c


# ── Payment Failure + Suspension ─────────────────────────────────────────


class TestPaymentFailure:
    def test_failure_increments_count(self, sub_a, plan_basic):
        PlatformService.activate_subscription(sub_a, plan_basic)
        PlatformService.record_payment_failure(sub_a, amount=Decimal("499.00"))
        sub_a.refresh_from_db()
        assert sub_a.payment_failure_count == 1
        assert sub_a.status == SaasStatus.PAST_DUE

    def test_three_failures_suspends(self, sub_a, plan_basic, biz_a):
        PlatformService.activate_subscription(sub_a, plan_basic)
        for _i in range(3):
            PlatformService.record_payment_failure(sub_a, amount=Decimal("499.00"))
            sub_a.refresh_from_db()

        assert sub_a.status == SaasStatus.SUSPENDED
        biz_a.refresh_from_db()
        assert biz_a.status == Status.SUSPENDED


# ── Suspension + Reactivation ─────────────────────────────────────────────


class TestSuspension:
    def test_suspend_business(self, biz_a, sub_a):
        PlatformService.suspend_business(biz_a)
        biz_a.refresh_from_db()
        sub_a.refresh_from_db()
        assert biz_a.status == Status.SUSPENDED
        assert sub_a.status == SaasStatus.SUSPENDED

    def test_reactivate_business(self, biz_a, sub_a):
        PlatformService.suspend_business(biz_a)
        PlatformService.reactivate_business(biz_a)
        biz_a.refresh_from_db()
        sub_a.refresh_from_db()
        assert biz_a.status == Status.ACTIVE
        assert sub_a.status == SaasStatus.PENDING  # nothing paid yet

    def test_suspended_business_blocked_from_api(self, biz_a, sub_a, client_a):
        PlatformService.suspend_business(biz_a)
        resp = client_a.get("/api/v1/customers/")
        assert resp.status_code == 403

    def test_super_admin_bypasses_suspension(self, biz_a, sub_a, client_super):
        PlatformService.suspend_business(biz_a)
        # SUPER_ADMIN should still be able to access platform endpoints
        resp = client_super.get("/api/v1/platform/businesses/")
        assert resp.status_code == 200


# ── Public Plans ─────────────────────────────────────────────────────────


class TestPublicPlans:
    def test_list_public_plans(self, plan_basic, plan_pro):
        client = APIClient()
        resp = client.get("/api/v1/pricing/")
        assert resp.status_code == 200
        assert len(resp.data) == 2
        # Should not expose razorpay_plan_id
        assert "razorpay_plan_id" not in resp.data[0]


# ── SUPER_ADMIN Platform Management ──────────────────────────────────────


class TestPlatformAdmin:
    def test_list_businesses(self, client_super, biz_a, owner_a, sub_a):
        resp = client_super.get("/api/v1/platform/businesses/")
        assert resp.status_code == 200
        assert resp.data["count"] >= 1

    def test_non_super_admin_blocked(self, client_a):
        resp = client_a.get("/api/v1/platform/businesses/")
        assert resp.status_code == 403

    def test_suspend_business_endpoint(self, client_super, biz_a, sub_a):
        resp = client_super.post(f"/api/v1/platform/businesses/{biz_a.id}/suspend/")
        assert resp.status_code == 200
        biz_a.refresh_from_db()
        assert biz_a.status == Status.SUSPENDED

    def test_reactivate_business_endpoint(self, client_super, biz_a, sub_a):
        PlatformService.suspend_business(biz_a)
        resp = client_super.post(f"/api/v1/platform/businesses/{biz_a.id}/reactivate/")
        assert resp.status_code == 200
        biz_a.refresh_from_db()
        assert biz_a.status == Status.ACTIVE

    def test_crud_plans(self, client_super):
        resp = client_super.post(
            "/api/v1/platform/plans/",
            {
                "name": "Starter",
                "price_monthly": "299.00",
                "max_customers": 25,
                "max_staff": 2,
                "features": ["25 customers"],
            },
            format="json",
        )
        assert resp.status_code == 201
        plan_id = resp.data["id"]

        resp = client_super.get(f"/api/v1/platform/plans/{plan_id}/")
        assert resp.status_code == 200
        assert resp.data["name"] == "Starter"

    def test_platform_stats(self, client_super, biz_a, sub_a):
        resp = client_super.get("/api/v1/platform/stats/")
        assert resp.status_code == 200
        assert "total_businesses" in resp.data

    def test_platform_payments_list(self, client_super, sub_a, plan_basic):
        PlatformService.activate_subscription(sub_a, plan_basic)
        PlatformService.record_payment_success(sub_a, amount=Decimal("499.00"))
        resp = client_super.get("/api/v1/platform/payments/")
        assert resp.status_code == 200
        assert resp.data["count"] == 1


# ── Quota Enforcement ────────────────────────────────────────────────────


class TestQuotaEnforcement:
    def test_monthly_plan_has_no_customer_limit(self, client_a, sub_a):
        resp = client_a.post(
            "/api/v1/customers/",
            {"name": "Test Customer", "phone": "9999999999"},
            format="json",
        )
        assert resp.status_code == 201

    def test_quota_enforced_on_plan_limit(self, client_a, sub_a, plan_basic, biz_a):
        # Activate plan with max_customers=50
        PlatformService.activate_subscription(sub_a, plan_basic)

        # Set max_customers to 1 for easy testing
        plan_basic.max_customers = 1
        plan_basic.save()

        # First customer should succeed
        resp = client_a.post(
            "/api/v1/customers/",
            {"name": "Customer 1", "phone": "1111111111"},
            format="json",
        )
        assert resp.status_code == 201

        # Second customer should be blocked (quota = 1)
        resp = client_a.post(
            "/api/v1/customers/",
            {"name": "Customer 2", "phone": "2222222222"},
            format="json",
        )
        assert resp.status_code == 402
        assert resp.json()["error"]["code"] == "QUOTA_EXCEEDED"


# ── Webhook ──────────────────────────────────────────────────────────────


class TestWebhook:
    def test_webhook_ignores_unknown_subscription(self, db):
        client = APIClient()
        resp = client.post(
            "/api/v1/webhooks/razorpay/",
            {
                "event": "subscription.charged",
                "payload": {
                    "subscription": {"entity": {"id": "sub_unknown"}},
                    "payment": {"entity": {"id": "pay_1", "amount": 49900}},
                },
            },
            format="json",
        )
        assert resp.status_code == 200

    def test_webhook_charge_success(self, sub_a, plan_basic):
        PlatformService.activate_subscription(sub_a, plan_basic, razorpay_subscription_id="sub_test123")
        client = APIClient()
        resp = client.post(
            "/api/v1/webhooks/razorpay/",
            {
                "event": "subscription.charged",
                "payload": {
                    "subscription": {"entity": {"id": "sub_test123"}},
                    "payment": {"entity": {"id": "pay_1", "amount": 49900, "order_id": "ord_1"}},
                },
            },
            format="json",
        )
        assert resp.status_code == 200
        assert SaasPayment.objects.filter(razorpay_payment_id="pay_1").exists()


# ── Monthly plan terms (docs/Monthly_Subscription_Plan.pdf) ──────────────

D0 = date(2026, 1, 10)  # first payment day used across the timeline tests


def pay(sub, day, amount=None):
    """Record exactly what is due on `day` (or `amount` if given)."""
    if amount is None:
        amount = PlatformService.amount_due(sub, day).total
    payment = PlatformService.record_manual_payment(sub, amount=amount, method="UPI", today=day)
    sub.refresh_from_db()
    return payment


class TestAddMonths:
    def test_same_day_next_month(self):
        assert add_months(date(2026, 1, 10), 1) == date(2026, 2, 10)

    def test_clamps_to_month_end(self):
        assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
        assert add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)

    def test_crosses_year(self):
        assert add_months(date(2026, 11, 30), 3) == date(2027, 2, 28)


class TestMonthlyPlan:
    def test_new_business_starts_pending_on_pdf_prices(self, sub_a):
        assert sub_a.status == SaasStatus.PENDING
        assert sub_a.setup_fee_paid is False
        assert sub_a.plan.price_monthly == Decimal("500.00")
        assert sub_a.plan.setup_fee == Decimal("2500.00")
        assert sub_a.plan.reactivation_fee == Decimal("1000.00")

    def test_start_billing_idempotent(self, biz_a):
        assert PlatformService.start_billing(biz_a).id == PlatformService.start_billing(biz_a).id

    def test_first_payment_is_setup_plus_first_month(self, sub_a):
        due = PlatformService.amount_due(sub_a, D0)
        assert due.setup_fee == Decimal("2500.00")
        assert due.monthly_fee == Decimal("500.00")
        assert due.reactivation_fee == Decimal("0.00")
        assert due.total == Decimal("3000.00")

    def test_first_payment_activates_for_one_month(self, sub_a):
        payment = pay(sub_a, D0)
        assert payment.amount == Decimal("3000.00")
        assert payment.setup_fee == Decimal("2500.00")
        assert payment.reactivation_fee == Decimal("0.00")
        assert sub_a.status == SaasStatus.ACTIVE
        assert sub_a.setup_fee_paid is True
        assert (sub_a.current_period_start, sub_a.current_period_end) == (D0, date(2026, 2, 10))

    def test_after_first_payment_500_each_month(self, sub_a):
        pay(sub_a, D0)
        due = PlatformService.amount_due(sub_a, date(2026, 2, 5))
        assert due.total == Decimal("500.00")
        assert due.setup_fee == Decimal("0.00")
        assert due.due_date == date(2026, 2, 10)

    def test_wrong_amount_rejected(self, sub_a):
        with pytest.raises(ValueError, match="3000"):
            PlatformService.record_manual_payment(sub_a, amount=Decimal("500.00"), method="UPI", today=D0)
        sub_a.refresh_from_db()
        assert sub_a.status == SaasStatus.PENDING
        assert not SaasPayment.objects.exists()

    def test_early_renewal_continues_from_due_date(self, sub_a):
        pay(sub_a, D0)
        pay(sub_a, date(2026, 2, 3))
        assert (sub_a.current_period_start, sub_a.current_period_end) == (
            date(2026, 2, 10),
            date(2026, 3, 10),
        )

    def test_late_renewal_within_grace_keeps_billing_date(self, sub_a):
        pay(sub_a, D0)
        PlatformService.run_billing_checks(date(2026, 2, 10))
        sub_a.refresh_from_db()
        assert sub_a.status == SaasStatus.PAST_DUE
        pay(sub_a, date(2026, 2, 14))
        assert sub_a.status == SaasStatus.ACTIVE
        assert sub_a.current_period_end == date(2026, 3, 10)


class TestBillingTimeline:
    def test_active_until_due_date(self, sub_a, biz_a):
        pay(sub_a, D0)
        PlatformService.run_billing_checks(date(2026, 2, 9))
        sub_a.refresh_from_db()
        assert sub_a.status == SaasStatus.ACTIVE

    def test_unpaid_on_due_date_is_past_due_but_usable(self, sub_a, biz_a):
        pay(sub_a, D0)
        PlatformService.run_billing_checks(date(2026, 2, 10))
        sub_a.refresh_from_db()
        biz_a.refresh_from_db()
        assert sub_a.status == SaasStatus.PAST_DUE
        assert biz_a.status == Status.ACTIVE

    def test_suspended_after_7_day_grace(self, sub_a, biz_a):
        pay(sub_a, D0)
        PlatformService.run_billing_checks(date(2026, 2, 10))
        PlatformService.run_billing_checks(date(2026, 2, 16))  # day 6 of grace
        biz_a.refresh_from_db()
        assert biz_a.status == Status.ACTIVE
        PlatformService.run_billing_checks(date(2026, 2, 17))  # day 7
        biz_a.refresh_from_db()
        sub_a.refresh_from_db()
        assert biz_a.status == Status.SUSPENDED
        assert sub_a.status == SaasStatus.SUSPENDED

    def test_missed_nights_still_suspend(self, sub_a, biz_a):
        """If the scheduler was down, one run moves ACTIVE straight through to SUSPENDED."""
        pay(sub_a, D0)
        PlatformService.run_billing_checks(date(2026, 3, 1))
        biz_a.refresh_from_db()
        assert biz_a.status == Status.SUSPENDED

    def test_pending_business_not_auto_suspended(self, sub_a, biz_a):
        PlatformService.run_billing_checks(date(2027, 1, 1))
        biz_a.refresh_from_db()
        assert biz_a.status == Status.ACTIVE

    def test_payment_after_suspension_restores_access_from_today(self, sub_a, biz_a):
        pay(sub_a, D0)
        PlatformService.run_billing_checks(date(2026, 2, 20))
        payment = pay(sub_a, date(2026, 2, 25))
        biz_a.refresh_from_db()
        assert payment.amount == Decimal("500.00")  # within 3 months — no reactivation fee
        assert biz_a.status == Status.ACTIVE
        assert sub_a.status == SaasStatus.ACTIVE
        assert (sub_a.current_period_start, sub_a.current_period_end) == (
            date(2026, 2, 25),
            date(2026, 3, 25),
        )

    def test_legacy_trial_suspended_after_end(self, biz_a):
        from apps.platform.models import SaasSubscription

        SaasSubscription.objects.create(business=biz_a, status=SaasStatus.TRIAL, trial_end_date=D0)
        PlatformService.run_billing_checks(D0 + timedelta(days=1))
        biz_a.refresh_from_db()
        assert biz_a.status == Status.SUSPENDED

    def test_billing_task_runs_checks(self, sub_a, biz_a):
        from apps.platform.tasks import run_billing_checks

        pay(sub_a, D0)
        sub_a.current_period_end = timezone.now().date() - timedelta(days=GRACE)
        sub_a.save()
        assert run_billing_checks() == {"past_due": 1, "suspended": 1}


GRACE = 7


class TestCancel:
    def test_cancel_keeps_access_until_paid_month_ends(self, sub_a, biz_a):
        pay(sub_a, D0)
        PlatformService.cancel_subscription(sub_a, today=date(2026, 1, 20))
        biz_a.refresh_from_db()
        assert sub_a.status == SaasStatus.CANCELLED
        assert biz_a.status == Status.ACTIVE

        PlatformService.run_billing_checks(date(2026, 2, 9))
        biz_a.refresh_from_db()
        assert biz_a.status == Status.ACTIVE

        PlatformService.run_billing_checks(date(2026, 2, 10))
        biz_a.refresh_from_db()
        sub_a.refresh_from_db()
        assert biz_a.status == Status.SUSPENDED
        assert sub_a.status == SaasStatus.CANCELLED  # stays CANCELLED, not SUSPENDED

    def test_cancel_before_first_payment_ends_access_now(self, sub_a, biz_a):
        PlatformService.cancel_subscription(sub_a, today=D0)
        biz_a.refresh_from_db()
        assert biz_a.status == Status.SUSPENDED

    def test_cannot_cancel_twice(self, sub_a):
        PlatformService.cancel_subscription(sub_a, today=D0)
        with pytest.raises(ValueError):
            PlatformService.cancel_subscription(sub_a, today=D0)

    def test_return_within_3_months_no_reactivation_fee(self, sub_a):
        pay(sub_a, D0)  # paid until 10 Feb
        PlatformService.cancel_subscription(sub_a, today=date(2026, 1, 20))
        due = PlatformService.amount_due(sub_a, date(2026, 5, 10))  # exactly 3 months later
        assert due.total == Decimal("500.00")
        assert due.setup_fee == Decimal("0.00")

    def test_return_after_more_than_3_months_pays_reactivation_fee(self, sub_a, biz_a):
        pay(sub_a, D0)
        PlatformService.cancel_subscription(sub_a, today=date(2026, 1, 20))
        PlatformService.run_billing_checks(date(2026, 2, 10))
        due = PlatformService.amount_due(sub_a, date(2026, 5, 11))
        assert due.reactivation_fee == Decimal("1000.00")
        assert due.setup_fee == Decimal("0.00")  # setup fee is never charged twice
        assert due.total == Decimal("1500.00")

        payment = pay(sub_a, date(2026, 5, 11))
        biz_a.refresh_from_db()
        assert payment.reactivation_fee == Decimal("1000.00")
        assert sub_a.status == SaasStatus.ACTIVE
        assert sub_a.cancelled_at is None
        assert biz_a.status == Status.ACTIVE
        assert sub_a.current_period_end == date(2026, 6, 11)

    def test_change_of_mind_before_month_ends_continues_billing_date(self, sub_a):
        pay(sub_a, D0)
        PlatformService.cancel_subscription(sub_a, today=date(2026, 1, 20))
        pay(sub_a, date(2026, 1, 25))
        assert sub_a.status == SaasStatus.ACTIVE
        assert (sub_a.current_period_start, sub_a.current_period_end) == (
            date(2026, 2, 10),
            date(2026, 3, 10),
        )


class TestBillingEndpoints:
    def test_owner_sees_amount_due(self, client_a, sub_a):
        resp = client_a.get("/api/v1/billing/")
        assert resp.status_code == 200
        assert resp.data["subscription"]["status"] == "PENDING"
        assert resp.data["subscription"]["amount_due"]["total"] == "3000.00"
        assert resp.data["subscription"]["plan_details"]["setup_fee"] == "2500.00"
        assert resp.data["payments"] == []

    def test_owner_sees_only_own_payments(self, client_a, client_b, sub_a, biz_b):
        pay(sub_a, timezone.now().date())
        PlatformService.start_billing(biz_b)
        assert len(client_a.get("/api/v1/billing/").data["payments"]) == 1
        assert client_b.get("/api/v1/billing/").data["payments"] == []

    def test_owner_can_cancel(self, client_a, sub_a):
        pay(sub_a, timezone.now().date())
        resp = client_a.post("/api/v1/billing/cancel/")
        assert resp.status_code == 200
        assert resp.data["subscription"]["status"] == "CANCELLED"

    def test_manager_cannot_cancel(self, manager_a, sub_a):
        c = APIClient()
        c.force_authenticate(user=manager_a)
        assert c.post("/api/v1/billing/cancel/").status_code == 403

    def test_cancel_twice_is_validation_error(self, client_a, sub_a):
        client_a.post("/api/v1/billing/cancel/")
        resp = client_a.post("/api/v1/billing/cancel/")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_signup_and_checkout_removed(self, client_a, plan_basic, db):
        assert APIClient().post("/api/v1/signup/", {}, format="json").status_code == 404
        resp = client_a.post("/api/v1/billing/checkout/", {"plan_id": str(plan_basic.id)}, format="json")
        assert resp.status_code == 404


class TestPlatformOnboarding:
    def test_super_admin_creates_business(self, client_super):
        resp = client_super.post(
            "/api/v1/platform/businesses/",
            {
                "business_name": "New Mess",
                "phone": "9000000000",
                "owner_username": "newowner",
                "owner_password": "securepass123",
                "owner_name": "New Owner",
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["saas_status"] == "PENDING"
        assert resp.data["amount_due"]["total"] == "3000.00"
        business = Business.objects.get(name="New Mess")
        assert business.users.get(username="newowner").role == Role.OWNER
        from apps.meals.models import Meal

        assert Meal.objects.filter(business=business).count() == 4

    def test_duplicate_owner_username_rejected(self, client_super, owner_a):
        resp = client_super.post(
            "/api/v1/platform/businesses/",
            {"business_name": "Dupe", "owner_username": "owner_a", "owner_password": "securepass123"},
            format="json",
        )
        assert resp.status_code == 400

    def test_owner_cannot_create_business(self, client_a):
        resp = client_a.post("/api/v1/platform/businesses/", {}, format="json")
        assert resp.status_code == 403

    def test_record_payment_endpoint(self, client_super, biz_a, sub_a, super_admin):
        url = f"/api/v1/platform/businesses/{biz_a.id}/record-payment/"
        resp = client_super.post(url, {"amount": "500.00", "method": "UPI"}, format="json")
        assert resp.status_code == 400
        assert "3000" in resp.json()["error"]["message"]

        resp = client_super.post(
            url, {"amount": "3000.00", "method": "CASH", "reference": "R1"}, format="json"
        )
        assert resp.status_code == 201
        assert resp.data["setup_fee"] == "2500.00"
        assert resp.data["method"] == "CASH"
        payment = SaasPayment.objects.get()
        assert payment.recorded_by == super_admin
        sub_a.refresh_from_db()
        assert sub_a.status == SaasStatus.ACTIVE

    def test_owner_cannot_record_own_payment(self, client_a, biz_a, sub_a):
        resp = client_a.post(
            f"/api/v1/platform/businesses/{biz_a.id}/record-payment/",
            {"amount": "3000.00", "method": "UPI"},
            format="json",
        )
        assert resp.status_code == 403

    def test_super_admin_cancels(self, client_super, biz_a, sub_a):
        resp = client_super.post(f"/api/v1/platform/businesses/{biz_a.id}/cancel/")
        assert resp.status_code == 200
        sub_a.refresh_from_db()
        assert sub_a.status == SaasStatus.CANCELLED
