"""Rahul Demo Dry-Run — full golden path via API calls (SD-03).

Covers the 12-step demo walkthrough:
 1. Create customer
 2. Create subscription (Monthly Lunch)
 3. Record full payment
 4. Verify ACTIVE
 5. Today's delivery exists
 6. Staff marks DELIVERED
 7. Skip tomorrow's delivery
 8. Verify SKIPPED
 9. Dashboard data
10. Customer detail
11. Admin sees history
12. Portal access
"""

import datetime
from datetime import timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.meals.models import Meal
from apps.plans.models import Plan
from apps.settings_app.models import BusinessSettings, SkipRule
from common.constants import Role


@pytest.fixture()
def biz(db):
    return Business.objects.create(name="Demo Mess", status="ACTIVE")


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
        username="demo_owner",
        password="pass",
        role=Role.OWNER,
        business=biz,
        name="Owner",
    )


@pytest.fixture()
def delivery_staff(biz):
    return User.objects.create_user(
        username="demo_delivery",
        password="pass",
        role=Role.DELIVERY_STAFF,
        business=biz,
        name="Delivery Guy",
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


def auth(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


TODAY = datetime.date.today()


@pytest.mark.django_db
class TestRahulDemo:
    """Full 12-step demo walkthrough via API."""

    def test_full_golden_path(self, biz, settings_row, owner, delivery_staff, meal, plan):
        client = auth(owner)

        # ── Step 1: Create customer ──────────────────────────────────
        resp = client.post(
            "/api/v1/customers/",
            {"name": "Rahul Kumar", "phone": "9876543210", "address": "Pune"},
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        customer_id = resp.json()["id"]

        # ── Step 2: Create subscription (Monthly Lunch) → PENDING ────
        resp = client.post(
            "/api/v1/subscriptions/",
            {"customer": customer_id, "plan": str(plan.id), "start_date": str(TODAY)},
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        sub_id = resp.json()["id"]
        assert resp.json()["status"] == "PENDING"

        # ── Step 3: Record full payment ──────────────────────────────
        resp = client.post(
            "/api/v1/payments/",
            {"subscription": sub_id, "amount": "2500.00", "method": "UPI", "payment_date": str(TODAY)},
            format="json",
        )
        assert resp.status_code == 201, resp.json()

        # ── Step 4: Verify subscription is ACTIVE ────────────────────
        resp = client.get(f"/api/v1/subscriptions/{sub_id}/")
        assert resp.json()["status"] == "ACTIVE"
        assert resp.json()["paid_amount"] == "2500.00"
        assert resp.json()["pending_amount"] == "0.00"

        # ── Step 5: Today's delivery exists ──────────────────────────
        resp = client.get("/api/v1/deliveries/today/")
        assert resp.status_code == 200
        results = resp.json()["results"]
        rahul_deliveries = [d for d in results if d["customer_name"] == "Rahul Kumar"]
        assert len(rahul_deliveries) >= 1
        delivery_id = rahul_deliveries[0]["id"]

        # ── Step 6: Staff marks DELIVERED ────────────────────────────
        staff_client = auth(delivery_staff)
        resp = staff_client.patch(
            f"/api/v1/deliveries/{delivery_id}/status/",
            {"status": "DELIVERED"},
            format="json",
        )
        assert resp.status_code == 200, resp.json()
        assert resp.json()["status"] == "DELIVERED"

        # ── Step 7: Skip tomorrow's delivery ─────────────────────────
        tomorrow = TODAY + timedelta(days=1)
        resp = client.get(
            f"/api/v1/deliveries/?date_from={tomorrow}&date_to={tomorrow}&subscription={sub_id}"
        )
        assert resp.status_code == 200
        tomorrow_results = resp.json()["results"]
        assert len(tomorrow_results) >= 1
        tomorrow_delivery_id = tomorrow_results[0]["id"]

        resp = client.post(
            f"/api/v1/deliveries/{tomorrow_delivery_id}/skip/",
            {"reason": "Out of town"},
            format="json",
        )
        assert resp.status_code == 200, resp.json()
        assert "skip_date" in resp.json()

        # ── Step 8: Verify delivery is SKIPPED ───────────────────────
        resp = client.get(f"/api/v1/deliveries/{tomorrow_delivery_id}/")
        assert resp.json()["status"] == "SKIPPED"

        # ── Step 9: Dashboard data ───────────────────────────────────
        resp = client.get("/api/v1/dashboard/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["subscriptions"]["active"] >= 1

        # ── Step 10: Customer detail ─────────────────────────────────
        resp = client.get(f"/api/v1/customers/{customer_id}/")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Rahul Kumar"

        # ── Step 11: Admin sees history ──────────────────────────────
        resp = client.get(f"/api/v1/subscriptions/?customer={customer_id}")
        assert resp.json()["count"] >= 1

        resp = client.get(f"/api/v1/payments/?customer={customer_id}")
        assert resp.json()["count"] >= 1

        resp = client.get(f"/api/v1/deliveries/?customer={customer_id}")
        assert resp.json()["count"] >= 1

        # ── Step 12: Portal access ───────────────────────────────────
        customer_obj = Customer.objects.get(id=customer_id)
        portal_user = User.objects.create_user(
            username="rahul_portal",
            password="pass",
            name="Rahul Kumar",
            role=Role.CUSTOMER,
            business=biz,
        )
        customer_obj.user = portal_user
        customer_obj.save(update_fields=["user", "updated_at"])

        portal_client = auth(portal_user)
        resp = portal_client.get("/api/v1/portal/dashboard/")
        assert resp.status_code == 200
        assert resp.json()["customer_name"] == "Rahul Kumar"
        assert resp.json()["active_subscription"] is not None
