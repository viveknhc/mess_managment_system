"""Definition-of-Done checklist tests (SD-04).

TestAdminDoD  — 14 admin capabilities (login, CRUD, views, reports).
TestCustomerDoD — 5 customer portal capabilities.
"""

import datetime
from datetime import timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.deliveries.models import Delivery, DeliveryStatus
from apps.meals.models import Meal
from apps.payments.services import PaymentService
from apps.plans.models import Plan
from apps.settings_app.models import BusinessSettings, SkipRule
from apps.subscriptions.services import SubscriptionService
from common.constants import Role, SubStatus

TODAY = datetime.date.today()


def auth(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ── Shared fixtures ──────────────────────────────────────────────────────


@pytest.fixture()
def biz(db):
    return Business.objects.create(name="DoD Mess", status="ACTIVE")


@pytest.fixture()
def settings_row(biz):
    return BusinessSettings.objects.create(
        business=biz,
        skip_rule=SkipRule.EXTEND,
        min_pause_days=1,
        max_pause_days=7,
    )


@pytest.fixture()
def owner(biz):
    return User.objects.create_user(
        username="dod_owner",
        password="pass",
        role=Role.OWNER,
        business=biz,
        name="Owner",
    )


@pytest.fixture()
def delivery_staff(biz):
    return User.objects.create_user(
        username="dod_delivery",
        password="pass",
        role=Role.DELIVERY_STAFF,
        business=biz,
        name="Delivery",
    )


@pytest.fixture()
def meal(biz):
    return Meal.objects.create(business=biz, name="Lunch")


@pytest.fixture()
def plan(biz, meal):
    return Plan.objects.create(
        business=biz,
        name="Monthly Lunch",
        meal=meal,
        duration_days=30,
        total_meals=30,
        price=Decimal("2500.00"),
        skip_allowed=True,
        pause_allowed=True,
    )


@pytest.fixture()
def customer(biz):
    return Customer.objects.create(business=biz, name="Test Customer", phone="9999999999")


@pytest.fixture()
def active_sub(biz, customer, plan):
    """Create a fully paid, ACTIVE subscription with deliveries."""
    sub = SubscriptionService.create_subscription(
        business_id=biz.id,
        customer=customer,
        plan=plan,
        start_date=TODAY,
    )
    PaymentService.record_payment(
        business_id=biz.id,
        subscription=sub,
        amount=plan.price,
        method="UPI",
        payment_date=TODAY,
    )
    sub.refresh_from_db()
    return sub


@pytest.fixture()
def expiring_sub(biz, meal):
    """Create an ACTIVE subscription expiring within 3 days."""
    plan_e = Plan.objects.create(
        business=biz,
        name="Expiring Plan",
        meal=meal,
        duration_days=30,
        total_meals=30,
        price=Decimal("2000.00"),
    )
    cust_e = Customer.objects.create(business=biz, name="Expiring Customer", phone="8888888888")
    start = TODAY - timedelta(days=28)
    sub = SubscriptionService.create_subscription(
        business_id=biz.id,
        customer=cust_e,
        plan=plan_e,
        start_date=start,
    )
    PaymentService.record_payment(
        business_id=biz.id,
        subscription=sub,
        amount=plan_e.price,
        method="CASH",
        payment_date=start,
    )
    sub.refresh_from_db()
    return sub


@pytest.fixture()
def expired_sub(biz, meal):
    """Create an EXPIRED subscription."""
    plan_x = Plan.objects.create(
        business=biz,
        name="Expired Plan",
        meal=meal,
        duration_days=30,
        total_meals=30,
        price=Decimal("1500.00"),
    )
    cust_x = Customer.objects.create(business=biz, name="Expired Customer", phone="7777777777")
    start = TODAY - timedelta(days=60)
    sub = SubscriptionService.create_subscription(
        business_id=biz.id,
        customer=cust_x,
        plan=plan_x,
        start_date=start,
    )
    PaymentService.record_payment(
        business_id=biz.id,
        subscription=sub,
        amount=plan_x.price,
        method="CASH",
        payment_date=start,
    )
    from apps.subscriptions.models import Subscription

    Subscription.objects.filter(id=sub.id).update(status=SubStatus.EXPIRED)
    sub.refresh_from_db()
    return sub


# ── Admin DoD ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAdminDoD:
    """14 admin capabilities — one test each."""

    def test_01_login(self, biz, owner):
        """Admin can obtain JWT tokens."""
        client = APIClient()
        resp = client.post(
            "/api/v1/auth/login/",
            {"username": "dod_owner", "password": "pass"},
            format="json",
        )
        assert resp.status_code == 200
        assert "access" in resp.json()
        assert resp.json()["user"]["role"] == "OWNER"

    def test_02_create_customer(self, owner):
        resp = auth(owner).post(
            "/api/v1/customers/",
            {"name": "New Customer", "phone": "1234567890"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "New Customer"

    def test_03_create_meal_plan(self, owner, meal):
        resp = auth(owner).post(
            "/api/v1/plans/",
            {
                "name": "Weekly Dinner",
                "meal": str(meal.id),
                "duration_days": 7,
                "total_meals": 7,
                "price": "700.00",
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Weekly Dinner"

    def test_04_create_subscription(self, owner, customer, plan):
        resp = auth(owner).post(
            "/api/v1/subscriptions/",
            {"customer": str(customer.id), "plan": str(plan.id), "start_date": str(TODAY)},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "PENDING"

    def test_05_record_payment(self, owner, active_sub):
        """Payment already recorded in fixture — verify via API."""
        resp = auth(owner).get("/api/v1/payments/")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_06_view_active_customers(self, owner, customer):
        resp = auth(owner).get("/api/v1/customers/?status=ACTIVE")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_07_view_expiring_subscriptions(self, owner, expiring_sub):
        resp = auth(owner).get("/api/v1/subscriptions/?status=ACTIVE")
        assert resp.status_code == 200
        # Expiring sub is ACTIVE with end_date within 3 days
        subs = resp.json()["results"]
        expiring = [s for s in subs if s["is_expiring"]]
        assert len(expiring) >= 1

    def test_08_view_expired_subscriptions(self, owner, expired_sub):
        resp = auth(owner).get("/api/v1/subscriptions/?status=EXPIRED")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_09_view_todays_deliveries(self, owner, active_sub):
        resp = auth(owner).get("/api/v1/deliveries/today/")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_10_mark_delivered(self, delivery_staff, active_sub):
        delivery = Delivery.objects.filter(
            subscription=active_sub,
            delivery_date=TODAY,
            status=DeliveryStatus.PENDING,
        ).first()
        assert delivery is not None
        resp = auth(delivery_staff).patch(
            f"/api/v1/deliveries/{delivery.id}/status/",
            {"status": "DELIVERED"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "DELIVERED"

    def test_11_mark_skipped(self, owner, active_sub):
        tomorrow = TODAY + timedelta(days=1)
        delivery = Delivery.objects.filter(
            subscription=active_sub,
            delivery_date=tomorrow,
            status=DeliveryStatus.PENDING,
        ).first()
        assert delivery is not None
        resp = auth(owner).post(
            f"/api/v1/deliveries/{delivery.id}/skip/",
            {"reason": "Holiday"},
            format="json",
        )
        assert resp.status_code == 200
        assert "skip_date" in resp.json()

    def test_12_view_payment_history(self, owner, active_sub):
        resp = auth(owner).get("/api/v1/payments/")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_13_view_basic_revenue(self, owner, active_sub):
        resp = auth(owner).get("/api/v1/reports/revenue/")
        assert resp.status_code == 200

    def test_14_view_meal_statistics(self, owner, active_sub):
        resp = auth(owner).get("/api/v1/reports/meals/")
        assert resp.status_code == 200


# ── Customer DoD ─────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCustomerDoD:
    """5 customer portal capabilities."""

    @pytest.fixture()
    def portal_setup(self, biz, settings_row, customer, active_sub):
        """Create a CUSTOMER user linked to the customer profile."""
        portal_user = User.objects.create_user(
            username="cust_portal",
            password="pass",
            role=Role.CUSTOMER,
            business=biz,
            name=customer.name,
        )
        customer.user = portal_user
        customer.save(update_fields=["user", "updated_at"])
        return portal_user, customer, active_sub

    def test_01_view_subscription_and_remaining_days(self, portal_setup):
        user, customer, active_sub = portal_setup
        resp = auth(user).get("/api/v1/portal/dashboard/")
        assert resp.status_code == 200
        assert resp.json()["customer_name"] == customer.name
        sub_data = resp.json()["active_subscription"]
        assert sub_data is not None
        assert sub_data["status"] == "ACTIVE"
        assert sub_data["remaining_days"] >= 0

    def test_02_view_payments(self, portal_setup):
        user, _, _ = portal_setup
        resp = auth(user).get("/api/v1/portal/payments/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_03_view_deliveries(self, portal_setup):
        user, _, _ = portal_setup
        resp = auth(user).get("/api/v1/portal/deliveries/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_04_skip_a_meal(self, portal_setup):
        user, customer, active_sub = portal_setup
        # Skip a future PENDING delivery via portal
        tomorrow = TODAY + timedelta(days=1)
        resp = auth(user).post(
            f"/api/v1/portal/subscriptions/{active_sub.id}/skip/",
            {"date": str(tomorrow), "reason": "Not hungry"},
            format="json",
        )
        assert resp.status_code == 200
        assert "skip_date" in resp.json()

    def test_05_view_subscriptions_list(self, portal_setup):
        user, _, _ = portal_setup
        resp = auth(user).get("/api/v1/portal/subscriptions/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1
