"""Payment tests: amount math, activation chain, golden workflow, isolation (PAY-07, PAY-12)."""

import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.meals.models import Meal
from apps.payments.models import PaymentMethod
from apps.payments.services import PaymentSelector, PaymentService
from apps.plans.models import Plan
from apps.subscriptions.services import SubscriptionService
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
def sub_pending(biz_a, cust_a, plan_a):
    return SubscriptionService.create_subscription(
        business_id=biz_a.id, customer=cust_a, plan=plan_a, start_date=datetime.date.today()
    )


@pytest.fixture()
def sub_b(biz_b):
    meal_b = Meal.objects.create(business=biz_b, name="Dinner")
    plan_b = Plan.objects.create(
        business=biz_b, name="Weekly", meal=meal_b, duration_days=7, total_meals=7, price=Decimal("500.00")
    )
    cust_b = Customer.objects.create(business=biz_b, name="Charlie")
    return SubscriptionService.create_subscription(
        business_id=biz_b.id, customer=cust_b, plan=plan_b, start_date=datetime.date.today()
    )


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


URL = "/api/v1/payments/"
TODAY = datetime.date.today()


# ── Service: record_payment math ─────────────────────────────────────────


@pytest.mark.django_db
class TestRecordPayment:
    def test_partial_payment(self, biz_a, sub_pending):
        payment = PaymentService.record_payment(
            business_id=biz_a.id,
            subscription=sub_pending,
            amount=Decimal("1000.00"),
            method=PaymentMethod.CASH,
            payment_date=TODAY,
        )
        assert payment.amount == Decimal("1000.00")
        sub_pending.refresh_from_db()
        assert sub_pending.paid_amount == Decimal("1000.00")
        assert sub_pending.pending_amount == Decimal("1500.00")
        assert sub_pending.status == SubStatus.PENDING  # not fully paid yet

    def test_full_payment_activates(self, biz_a, sub_pending):
        PaymentService.record_payment(
            business_id=biz_a.id,
            subscription=sub_pending,
            amount=Decimal("2500.00"),
            method=PaymentMethod.UPI,
            payment_date=TODAY,
        )
        sub_pending.refresh_from_db()
        assert sub_pending.paid_amount == Decimal("2500.00")
        assert sub_pending.pending_amount == Decimal("0.00")
        assert sub_pending.status == SubStatus.ACTIVE

    def test_two_partial_payments_activate(self, biz_a, sub_pending):
        PaymentService.record_payment(
            business_id=biz_a.id,
            subscription=sub_pending,
            amount=Decimal("1500.00"),
            method=PaymentMethod.CASH,
            payment_date=TODAY,
        )
        assert sub_pending.status == SubStatus.PENDING

        PaymentService.record_payment(
            business_id=biz_a.id,
            subscription=sub_pending,
            amount=Decimal("1000.00"),
            method=PaymentMethod.CASH,
            payment_date=TODAY,
        )
        sub_pending.refresh_from_db()
        assert sub_pending.status == SubStatus.ACTIVE
        assert sub_pending.pending_amount == Decimal("0.00")

    def test_overpay_rejected(self, biz_a, sub_pending):
        with pytest.raises(ValueError, match="exceeds pending"):
            PaymentService.record_payment(
                business_id=biz_a.id,
                subscription=sub_pending,
                amount=Decimal("3000.00"),
                method=PaymentMethod.CASH,
                payment_date=TODAY,
            )

    def test_payment_on_cancelled_rejected(self, biz_a, sub_pending):
        SubscriptionService.cancel(sub_pending)
        with pytest.raises(ValueError, match="CANCELLED"):
            PaymentService.record_payment(
                business_id=biz_a.id,
                subscription=sub_pending,
                amount=Decimal("100.00"),
                method=PaymentMethod.CASH,
                payment_date=TODAY,
            )

    def test_cross_business_rejected(self, biz_a, sub_b):
        with pytest.raises(ValueError, match="does not belong"):
            PaymentService.record_payment(
                business_id=biz_a.id,
                subscription=sub_b,
                amount=Decimal("100.00"),
                method=PaymentMethod.CASH,
                payment_date=TODAY,
            )

    def test_zero_amount_rejected(self, biz_a, sub_pending):
        with pytest.raises(ValueError, match="positive"):
            PaymentService.record_payment(
                business_id=biz_a.id,
                subscription=sub_pending,
                amount=Decimal("0.00"),
                method=PaymentMethod.CASH,
                payment_date=TODAY,
            )


# ── Payment summary selector ─────────────────────────────────────────────


@pytest.mark.django_db
class TestPaymentSummary:
    def test_summary(self, biz_a, sub_pending):
        PaymentService.record_payment(
            business_id=biz_a.id,
            subscription=sub_pending,
            amount=Decimal("1000.00"),
            method=PaymentMethod.CASH,
            payment_date=TODAY,
        )
        summary = PaymentSelector.get_summary(biz_a.id)
        assert summary["today"] == Decimal("1000.00")
        assert summary["month"] == Decimal("1000.00")
        assert summary["pending"] == Decimal("1500.00")

    def test_summary_empty(self, biz_a):
        summary = PaymentSelector.get_summary(biz_a.id)
        assert summary["today"] == Decimal("0.00")


# ── API endpoints ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPaymentAPI:
    def test_create_payment(self, owner_a, sub_pending):
        resp = auth_client(owner_a).post(
            URL,
            {
                "subscription": str(sub_pending.id),
                "amount": "1000.00",
                "method": "CASH",
                "payment_date": str(TODAY),
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["amount"] == "1000.00"

    def test_list_payments(self, owner_a, biz_a, sub_pending):
        PaymentService.record_payment(
            business_id=biz_a.id,
            subscription=sub_pending,
            amount=Decimal("500.00"),
            method=PaymentMethod.CASH,
            payment_date=TODAY,
        )
        resp = auth_client(owner_a).get(URL)
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_filter_by_customer(self, owner_a, biz_a, sub_pending, cust_a):
        PaymentService.record_payment(
            business_id=biz_a.id,
            subscription=sub_pending,
            amount=Decimal("500.00"),
            method=PaymentMethod.CASH,
            payment_date=TODAY,
        )
        resp = auth_client(owner_a).get(URL, {"customer": str(cust_a.id)})
        assert resp.json()["count"] == 1

    def test_delivery_can_view(self, delivery_a, biz_a, sub_pending):
        PaymentService.record_payment(
            business_id=biz_a.id,
            subscription=sub_pending,
            amount=Decimal("500.00"),
            method=PaymentMethod.CASH,
            payment_date=TODAY,
        )
        resp = auth_client(delivery_a).get(URL)
        assert resp.status_code == 200

    def test_delivery_cannot_create(self, delivery_a, sub_pending):
        resp = auth_client(delivery_a).post(
            URL,
            {"subscription": str(sub_pending.id), "amount": "100.00", "method": "CASH"},
            format="json",
        )
        assert resp.status_code == 403

    def test_summary_endpoint(self, owner_a, biz_a, sub_pending):
        PaymentService.record_payment(
            business_id=biz_a.id,
            subscription=sub_pending,
            amount=Decimal("1000.00"),
            method=PaymentMethod.CASH,
            payment_date=TODAY,
        )
        resp = auth_client(owner_a).get(f"{URL}summary/")
        assert resp.status_code == 200
        assert Decimal(str(resp.json()["today"])) == Decimal("1000.00")

    def test_overpay_via_api_returns_400(self, owner_a, sub_pending):
        resp = auth_client(owner_a).post(
            URL,
            {"subscription": str(sub_pending.id), "amount": "9999.00", "method": "CASH"},
            format="json",
        )
        assert resp.status_code == 400


# ── Golden workflow e2e (PAY-12) ─────────────────────────────────────────


@pytest.mark.django_db
class TestGoldenWorkflow:
    """Customer → Plan → Subscription → Payment → ACTIVE."""

    def test_full_golden_path(self, owner_a, biz_a, meal_a):
        client = auth_client(owner_a)

        # 1. Create customer
        resp = client.post("/api/v1/customers/", {"name": "Rahul", "phone": "9876543210"}, format="json")
        assert resp.status_code == 201
        customer_id = resp.json()["id"]

        # 2. Create plan
        resp = client.post(
            "/api/v1/plans/",
            {
                "name": "Daily Lunch",
                "meal": str(meal_a.id),
                "duration_days": 30,
                "total_meals": 30,
                "price": "1500.00",
            },
            format="json",
        )
        assert resp.status_code == 201
        plan_id = resp.json()["id"]

        # 3. Create subscription → PENDING
        resp = client.post(
            "/api/v1/subscriptions/",
            {"customer": customer_id, "plan": plan_id, "start_date": str(TODAY)},
            format="json",
        )
        assert resp.status_code == 201
        sub_id = resp.json()["id"]
        assert resp.json()["status"] == "PENDING"
        assert resp.json()["pending_amount"] == "1500.00"

        # 4. Record full payment → ACTIVE
        resp = client.post(
            URL,
            {"subscription": sub_id, "amount": "1500.00", "method": "UPI"},
            format="json",
        )
        assert resp.status_code == 201

        # 5. Verify subscription is now ACTIVE
        resp = client.get(f"/api/v1/subscriptions/{sub_id}/")
        assert resp.json()["status"] == "ACTIVE"
        assert resp.json()["paid_amount"] == "1500.00"
        assert resp.json()["pending_amount"] == "0.00"

    def test_partial_then_full(self, owner_a, biz_a, sub_pending):
        client = auth_client(owner_a)

        # Partial payment — stays PENDING
        resp = client.post(
            URL,
            {"subscription": str(sub_pending.id), "amount": "1500.00", "method": "CASH"},
            format="json",
        )
        assert resp.status_code == 201
        sub_resp = client.get(f"/api/v1/subscriptions/{sub_pending.id}/")
        assert sub_resp.json()["status"] == "PENDING"

        # Remaining payment — becomes ACTIVE
        resp = client.post(
            URL,
            {"subscription": str(sub_pending.id), "amount": "1000.00", "method": "UPI"},
            format="json",
        )
        assert resp.status_code == 201
        sub_resp = client.get(f"/api/v1/subscriptions/{sub_pending.id}/")
        assert sub_resp.json()["status"] == "ACTIVE"


# ── Tenant isolation ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPaymentIsolation:
    def test_owner_b_cannot_see_biz_a_payments(self, owner_b, biz_a, sub_pending):
        PaymentService.record_payment(
            business_id=biz_a.id,
            subscription=sub_pending,
            amount=Decimal("500.00"),
            method=PaymentMethod.CASH,
            payment_date=TODAY,
        )
        resp = auth_client(owner_b).get(URL)
        assert resp.json()["count"] == 0

    def test_owner_b_cannot_pay_biz_a_sub(self, owner_b, sub_pending):
        resp = auth_client(owner_b).post(
            URL,
            {"subscription": str(sub_pending.id), "amount": "100.00", "method": "CASH"},
            format="json",
        )
        assert resp.status_code == 400
