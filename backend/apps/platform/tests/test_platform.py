"""Platform billing module tests — trial, quota, suspension, signup, SUPER_ADMIN isolation."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.platform.models import SaasPayment, SaasPlan, SaasStatus
from apps.platform.services import PlatformService
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
def trial_sub(biz_a):
    return PlatformService.start_trial(biz_a)


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


# ── Trial ─────────────────────────────────────────────────────────────────


class TestTrial:
    def test_start_trial_creates_subscription(self, biz_a):
        sub = PlatformService.start_trial(biz_a)
        assert sub.status == SaasStatus.TRIAL
        assert sub.trial_end_date == timezone.now().date() + timedelta(days=30)
        assert sub.plan is None

    def test_start_trial_idempotent(self, biz_a):
        sub1 = PlatformService.start_trial(biz_a)
        sub2 = PlatformService.start_trial(biz_a)
        assert sub1.id == sub2.id

    def test_trial_days_remaining(self, trial_sub):
        assert trial_sub.trial_end_date == timezone.now().date() + timedelta(days=30)


# ── Subscription Activation ──────────────────────────────────────────────


class TestActivation:
    def test_activate_subscription(self, trial_sub, plan_basic):
        PlatformService.activate_subscription(trial_sub, plan_basic)
        trial_sub.refresh_from_db()
        assert trial_sub.status == SaasStatus.ACTIVE
        assert trial_sub.plan == plan_basic
        assert trial_sub.current_period_start == timezone.now().date()

    def test_record_payment_success(self, trial_sub, plan_basic):
        PlatformService.activate_subscription(trial_sub, plan_basic)
        payment = PlatformService.record_payment_success(
            trial_sub, amount=Decimal("499.00"), razorpay_payment_id="pay_123"
        )
        assert payment.status == "PAID"
        assert payment.amount == Decimal("499.00")
        trial_sub.refresh_from_db()
        assert trial_sub.payment_failure_count == 0


# ── Payment Failure + Suspension ─────────────────────────────────────────


class TestPaymentFailure:
    def test_failure_increments_count(self, trial_sub, plan_basic):
        PlatformService.activate_subscription(trial_sub, plan_basic)
        PlatformService.record_payment_failure(trial_sub, amount=Decimal("499.00"))
        trial_sub.refresh_from_db()
        assert trial_sub.payment_failure_count == 1
        assert trial_sub.status == SaasStatus.PAST_DUE

    def test_three_failures_suspends(self, trial_sub, plan_basic, biz_a):
        PlatformService.activate_subscription(trial_sub, plan_basic)
        for _i in range(3):
            PlatformService.record_payment_failure(trial_sub, amount=Decimal("499.00"))
            trial_sub.refresh_from_db()

        assert trial_sub.status == SaasStatus.SUSPENDED
        biz_a.refresh_from_db()
        assert biz_a.status == Status.SUSPENDED


# ── Suspension + Reactivation ─────────────────────────────────────────────


class TestSuspension:
    def test_suspend_business(self, biz_a, trial_sub):
        PlatformService.suspend_business(biz_a)
        biz_a.refresh_from_db()
        trial_sub.refresh_from_db()
        assert biz_a.status == Status.SUSPENDED
        assert trial_sub.status == SaasStatus.SUSPENDED

    def test_reactivate_business(self, biz_a, trial_sub):
        PlatformService.suspend_business(biz_a)
        PlatformService.reactivate_business(biz_a)
        biz_a.refresh_from_db()
        trial_sub.refresh_from_db()
        assert biz_a.status == Status.ACTIVE
        assert trial_sub.status == SaasStatus.TRIAL

    def test_suspended_business_blocked_from_api(self, biz_a, trial_sub, client_a):
        PlatformService.suspend_business(biz_a)
        resp = client_a.get("/api/v1/customers/")
        assert resp.status_code == 403

    def test_super_admin_bypasses_suspension(self, biz_a, trial_sub, client_super):
        PlatformService.suspend_business(biz_a)
        # SUPER_ADMIN should still be able to access platform endpoints
        resp = client_super.get("/api/v1/platform/businesses/")
        assert resp.status_code == 200


# ── Signup ────────────────────────────────────────────────────────────────


class TestSignup:
    def test_signup_creates_business_and_trial(self, db):
        client = APIClient()
        resp = client.post(
            "/api/v1/signup/",
            {
                "business_name": "New Mess",
                "owner_username": "newowner",
                "owner_password": "securepass123",
                "owner_name": "New Owner",
                "owner_email": "new@example.com",
            },
            format="json",
        )
        assert resp.status_code == 201
        assert "access" in resp.data
        assert "refresh" in resp.data
        assert resp.data["user"]["role"] == Role.OWNER
        assert resp.data["business"]["name"] == "New Mess"

        business = Business.objects.get(name="New Mess")
        sub = business.saas_subscription
        assert sub.status == SaasStatus.TRIAL

    def test_signup_duplicate_username_fails(self, owner_a):
        client = APIClient()
        resp = client.post(
            "/api/v1/signup/",
            {
                "business_name": "Dupe",
                "owner_username": "owner_a",
                "owner_password": "securepass123",
            },
            format="json",
        )
        assert resp.status_code == 400


# ── Billing Endpoints ────────────────────────────────────────────────────


class TestBilling:
    def test_billing_status(self, client_a, trial_sub):
        resp = client_a.get("/api/v1/billing/")
        assert resp.status_code == 200
        assert resp.data["subscription"]["status"] == "TRIAL"
        assert resp.data["subscription"]["days_remaining"] == 30

    def test_checkout_activates_plan(self, client_a, trial_sub, plan_basic):
        resp = client_a.post(
            "/api/v1/billing/checkout/",
            {"plan_id": str(plan_basic.id)},
            format="json",
        )
        assert resp.status_code == 200
        trial_sub.refresh_from_db()
        assert trial_sub.plan == plan_basic
        assert trial_sub.status == SaasStatus.ACTIVE


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
    def test_list_businesses(self, client_super, biz_a, owner_a, trial_sub):
        resp = client_super.get("/api/v1/platform/businesses/")
        assert resp.status_code == 200
        assert resp.data["count"] >= 1

    def test_non_super_admin_blocked(self, client_a):
        resp = client_a.get("/api/v1/platform/businesses/")
        assert resp.status_code == 403

    def test_suspend_business_endpoint(self, client_super, biz_a, trial_sub):
        resp = client_super.post(f"/api/v1/platform/businesses/{biz_a.id}/suspend/")
        assert resp.status_code == 200
        biz_a.refresh_from_db()
        assert biz_a.status == Status.SUSPENDED

    def test_reactivate_business_endpoint(self, client_super, biz_a, trial_sub):
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

    def test_platform_stats(self, client_super, biz_a, trial_sub):
        resp = client_super.get("/api/v1/platform/stats/")
        assert resp.status_code == 200
        assert "total_businesses" in resp.data

    def test_platform_payments_list(self, client_super, trial_sub, plan_basic):
        PlatformService.activate_subscription(trial_sub, plan_basic)
        PlatformService.record_payment_success(trial_sub, amount=Decimal("499.00"))
        resp = client_super.get("/api/v1/platform/payments/")
        assert resp.status_code == 200
        assert resp.data["count"] == 1


# ── Quota Enforcement ────────────────────────────────────────────────────


class TestQuotaEnforcement:
    def test_quota_not_enforced_during_trial(self, client_a, trial_sub):
        # Trial has no limits, should be able to create customers
        resp = client_a.post(
            "/api/v1/customers/",
            {"name": "Test Customer", "phone": "9999999999"},
            format="json",
        )
        assert resp.status_code == 201

    def test_quota_enforced_on_plan_limit(self, client_a, trial_sub, plan_basic, biz_a):
        # Activate plan with max_customers=50
        PlatformService.activate_subscription(trial_sub, plan_basic)

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

    def test_webhook_charge_success(self, trial_sub, plan_basic):
        PlatformService.activate_subscription(trial_sub, plan_basic, razorpay_subscription_id="sub_test123")
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


# ── Celery Tasks ─────────────────────────────────────────────────────────


class TestCeleryTasks:
    def test_trial_expiration_task(self, biz_a, trial_sub):
        # Set trial to expired
        trial_sub.trial_end_date = timezone.now().date() - timedelta(days=1)
        trial_sub.save()

        from apps.platform.tasks import check_trial_expirations

        count = check_trial_expirations()
        assert count == 1
        biz_a.refresh_from_db()
        assert biz_a.status == Status.SUSPENDED

    def test_trial_not_expired_yet(self, biz_a, trial_sub):
        from apps.platform.tasks import check_trial_expirations

        count = check_trial_expirations()
        assert count == 0
        biz_a.refresh_from_db()
        assert biz_a.status == Status.ACTIVE
