"""Dashboard aggregator tests (DB-02)."""

import datetime
from datetime import timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.dashboard.selectors import get_dashboard_data
from apps.deliveries.services import DeliveryService
from apps.meals.models import Meal
from apps.payments.models import PaymentMethod
from apps.payments.services import PaymentService
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription
from apps.subscriptions.services import SubscriptionService
from common.constants import Role, SubStatus

TODAY = datetime.date.today()


@pytest.fixture()
def biz_a(db):
    return Business.objects.create(name="Mess A")


@pytest.fixture()
def owner_a(biz_a):
    return User.objects.create_user(username="owner_a", password="pass", role=Role.OWNER, business=biz_a)


@pytest.fixture()
def delivery_staff(biz_a):
    return User.objects.create_user(
        username="delivery_a", password="pass", role=Role.DELIVERY_STAFF, business=biz_a
    )


@pytest.fixture()
def seeded(biz_a):
    """Seed a complete scenario for dashboard numbers."""
    meal = Meal.objects.create(business=biz_a, name="Lunch")
    plan = Plan.objects.create(
        business=biz_a, name="Weekly", meal=meal, duration_days=7, total_meals=7, price=Decimal("500.00")
    )

    # 3 active customers
    custs = [Customer.objects.create(business=biz_a, name=f"Cust {i}") for i in range(3)]

    # 2 active subscriptions (fully paid), 1 pending
    sub1 = SubscriptionService.create_subscription(
        business_id=biz_a.id, customer=custs[0], plan=plan, start_date=TODAY
    )
    PaymentService.record_payment(
        business_id=biz_a.id,
        subscription=sub1,
        amount=Decimal("500.00"),
        method=PaymentMethod.CASH,
        payment_date=TODAY,
    )
    DeliveryService.generate_delivery_schedule(sub1)

    sub2 = SubscriptionService.create_subscription(
        business_id=biz_a.id, customer=custs[1], plan=plan, start_date=TODAY
    )
    PaymentService.record_payment(
        business_id=biz_a.id,
        subscription=sub2,
        amount=Decimal("500.00"),
        method=PaymentMethod.UPI,
        payment_date=TODAY,
    )
    DeliveryService.generate_delivery_schedule(sub2)

    sub3 = SubscriptionService.create_subscription(
        business_id=biz_a.id, customer=custs[2], plan=plan, start_date=TODAY
    )
    # sub3 stays PENDING — partial payment
    PaymentService.record_payment(
        business_id=biz_a.id,
        subscription=sub3,
        amount=Decimal("200.00"),
        method=PaymentMethod.CASH,
        payment_date=TODAY,
    )

    # 1 expiring subscription (end_date = today + 2)
    Subscription.objects.create(
        business=biz_a,
        customer=custs[0],
        plan=plan,
        start_date=TODAY - timedelta(days=5),
        end_date=TODAY + timedelta(days=2),
        status=SubStatus.ACTIVE,
        total_amount=Decimal("500"),
        paid_amount=Decimal("500"),
        pending_amount=Decimal("0"),
        remaining_meals=2,
    )

    return {"custs": custs, "subs": [sub1, sub2, sub3], "plan": plan}


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestDashboardSelector:
    def test_customer_counts(self, biz_a, seeded):
        data = get_dashboard_data(biz_a.id)
        assert data["customers"]["active"] == 3

    def test_subscription_counts(self, biz_a, seeded):
        data = get_dashboard_data(biz_a.id)
        # 2 active (paid) + 1 expiring = 3 active, 1 pending
        assert data["subscriptions"]["active"] == 3  # 2 paid + 1 expiring fixture
        assert data["subscriptions"]["pending"] == 1

    def test_expiring_counts(self, biz_a, seeded):
        data = get_dashboard_data(biz_a.id)
        assert data["subscriptions"]["expiring_3_days"] >= 1

    def test_delivery_counts(self, biz_a, seeded):
        data = get_dashboard_data(biz_a.id)
        # 2 active subs with deliveries generated for today
        assert data["deliveries"]["total_today"] == 2
        assert data["deliveries"]["pending"] == 2

    def test_payment_totals(self, biz_a, seeded):
        data = get_dashboard_data(biz_a.id)
        assert data["payments"]["today_revenue"] == Decimal("1200.00")  # 500 + 500 + 200
        assert data["payments"]["total_pending"] == Decimal("300.00")  # sub3 pending

    def test_meals_today(self, biz_a, seeded):
        data = get_dashboard_data(biz_a.id)
        assert len(data["meals_today"]) == 1
        assert data["meals_today"][0]["meal__name"] == "Lunch"


@pytest.mark.django_db
class TestDashboardAPI:
    def test_owner_can_access(self, owner_a, seeded):
        resp = auth_client(owner_a).get("/api/v1/dashboard/")
        assert resp.status_code == 200
        assert "customers" in resp.json()
        assert "subscriptions" in resp.json()
        assert "deliveries" in resp.json()
        assert "payments" in resp.json()

    def test_delivery_staff_denied(self, delivery_staff):
        resp = auth_client(delivery_staff).get("/api/v1/dashboard/")
        assert resp.status_code == 403

    def test_unauthenticated_denied(self, db):
        resp = APIClient().get("/api/v1/dashboard/")
        assert resp.status_code == 401
