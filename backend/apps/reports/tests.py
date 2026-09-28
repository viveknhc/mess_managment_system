"""Report tests (R-06)."""

import datetime
from datetime import timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.deliveries.services import DeliveryService
from apps.meals.models import Meal
from apps.payments.models import PaymentMethod
from apps.payments.services import PaymentService
from apps.plans.models import Plan
from apps.reports.selectors import customer_report, meal_report, revenue_report, subscription_report
from apps.subscriptions.services import SubscriptionService
from common.constants import Role

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
        username="del_a", password="pass", role=Role.DELIVERY_STAFF, business=biz_a
    )


@pytest.fixture()
def seeded(biz_a):
    """Seed data for report testing."""
    meal = Meal.objects.create(business=biz_a, name="Lunch")
    plan = Plan.objects.create(
        business=biz_a, name="Weekly", meal=meal, duration_days=7, total_meals=7, price=Decimal("500.00")
    )
    c1 = Customer.objects.create(business=biz_a, name="Alice")
    c2 = Customer.objects.create(business=biz_a, name="Bob")
    c3 = Customer.objects.create(business=biz_a, name="Charlie", status="INACTIVE")

    sub1 = SubscriptionService.create_subscription(
        business_id=biz_a.id, customer=c1, plan=plan, start_date=TODAY
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
        business_id=biz_a.id, customer=c2, plan=plan, start_date=TODAY
    )
    # Partial payment
    PaymentService.record_payment(
        business_id=biz_a.id,
        subscription=sub2,
        amount=Decimal("200.00"),
        method=PaymentMethod.UPI,
        payment_date=TODAY,
    )

    return {"customers": [c1, c2, c3], "subs": [sub1, sub2], "plan": plan}


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestCustomerReport:
    def test_counts(self, biz_a, seeded):
        r = customer_report(biz_a.id)
        assert r["total"] == 3
        assert r["active"] == 2
        assert r["inactive"] == 1


@pytest.mark.django_db
class TestSubscriptionReport:
    def test_counts(self, biz_a, seeded):
        r = subscription_report(biz_a.id)
        assert r["active"] == 1  # sub1 fully paid
        assert r["pending"] == 1  # sub2 partial


@pytest.mark.django_db
class TestRevenueReport:
    def test_totals(self, biz_a, seeded):
        r = revenue_report(biz_a.id)
        assert r["total_collected"] == Decimal("700.00")
        assert r["total_pending"] == Decimal("300.00")
        assert len(r["daily"]) == 1

    def test_date_filter(self, biz_a, seeded):
        r = revenue_report(biz_a.id, date_from=TODAY + timedelta(days=1))
        assert r["total_collected"] == Decimal("0.00")


@pytest.mark.django_db
class TestMealReport:
    def test_counts(self, biz_a, seeded):
        r = meal_report(biz_a.id)
        assert len(r["by_meal"]) == 1
        assert r["by_meal"][0]["meal_name"] == "Lunch"
        assert r["by_meal"][0]["pending"] == 7  # sub1 has 7 deliveries


@pytest.mark.django_db
class TestReportAPI:
    def test_customer_report_endpoint(self, owner_a, seeded):
        resp = auth_client(owner_a).get("/api/v1/reports/customers/")
        assert resp.status_code == 200
        assert resp.json()["total"] == 3

    def test_subscription_report_endpoint(self, owner_a, seeded):
        resp = auth_client(owner_a).get("/api/v1/reports/subscriptions/")
        assert resp.status_code == 200

    def test_revenue_report_endpoint(self, owner_a, seeded):
        resp = auth_client(owner_a).get("/api/v1/reports/revenue/")
        assert resp.status_code == 200

    def test_meal_report_endpoint(self, owner_a, seeded):
        resp = auth_client(owner_a).get("/api/v1/reports/meals/")
        assert resp.status_code == 200

    def test_payment_report_endpoint(self, owner_a, seeded):
        resp = auth_client(owner_a).get("/api/v1/reports/payments/")
        assert resp.status_code == 200

    def test_date_range_params(self, owner_a, seeded):
        resp = auth_client(owner_a).get(
            "/api/v1/reports/revenue/", {"date_from": str(TODAY), "date_to": str(TODAY)}
        )
        assert resp.status_code == 200

    def test_delivery_staff_denied(self, delivery_staff, seeded):
        resp = auth_client(delivery_staff).get("/api/v1/reports/customers/")
        assert resp.status_code == 403
