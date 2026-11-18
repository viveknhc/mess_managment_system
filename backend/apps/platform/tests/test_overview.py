"""SUPER_ADMIN mess overview — GET /platform/businesses/{id}/overview/."""

from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.customization.registry import ONLINE_PAYMENTS, REPORTS, SKIP
from apps.customization.services import FeatureService, PolicyService
from apps.meals.models import Meal
from apps.payments.services import PaymentService
from apps.plans.models import Plan
from apps.platform.models import SaasPlan
from apps.platform.services import PlatformService
from apps.settings_app.models import BusinessSettings
from apps.subscriptions.services import SubscriptionService
from common.constants import Role

TODAY = timezone.localdate()


@pytest.fixture()
def mess(db):
    biz, owner = PlatformService.create_business(
        name="Overview Mess",
        owner_username="ov_owner",
        owner_password="x",
        owner_name="Ovi",
        owner_email="o@x.in",
    )
    plan = SaasPlan.objects.create(name="Basic", price_monthly=Decimal("299.00"), feature_keys=[REPORTS])
    sub = biz.saas_subscription
    sub.plan = plan
    sub.save()
    FeatureService.set_overrides(biz.id, {ONLINE_PAYMENTS: True})
    PolicyService.set_policy(biz.id, SKIP, "EXTEND")
    BusinessSettings.objects.create(business=biz, max_pause_days=9)
    User.objects.create_user(username="ov_cook", password="x", role=Role.KITCHEN_STAFF, business=biz)
    meal_plan = Plan.objects.create(
        business=biz,
        name="Monthly",
        meal=Meal.objects.get(business=biz, name="Lunch"),
        duration_days=30,
        total_meals=30,
        price=Decimal("3000.00"),
    )
    for i in range(2):
        customer = Customer.objects.create(business=biz, name=f"C{i}", phone=f"90000000{i}")
        s = SubscriptionService.create_subscription(
            business_id=biz.id, customer=customer, plan=meal_plan, start_date=TODAY
        )
        if i == 0:
            PaymentService.record_payment(
                business_id=biz.id, subscription=s, amount=meal_plan.price, method="UPI", payment_date=TODAY
            )
    return biz


@pytest.fixture()
def super_admin(db):
    return User.objects.create_user(username="ov_root", password="x", role=Role.SUPER_ADMIN)


def _get(user, biz):
    client = APIClient()
    client.force_authenticate(user)
    return client.get(f"/api/v1/platform/businesses/{biz.id}/overview/")


def test_overview_has_everything(super_admin, mess):
    resp = _get(super_admin, mess)
    assert resp.status_code == 200
    d = resp.json()
    assert d["business"]["name"] == "Overview Mess"
    assert d["billing"]["plan_name"] == "Basic"
    assert d["billing"]["plan_details"]["feature_keys"] == [REPORTS]
    features = {f["key"]: f for f in d["features"]}
    assert features[REPORTS] == {**features[REPORTS], "enabled": True, "source": "plan"}
    assert features[ONLINE_PAYMENTS]["enabled"] and features[ONLINE_PAYMENTS]["source"] == "override"
    assert not features[ONLINE_PAYMENTS]["inherited"]
    skip = next(p for p in d["policies"] if p["point"] == SKIP)
    assert skip["policy"] == "EXTEND" and not skip["is_default"]
    assert d["settings"]["max_pause_days"] == 9
    assert "razorpay_key_id" not in d["settings"]
    assert {u["username"] for u in d["team"]} == {"ov_owner", "ov_cook"}
    assert d["customers"]["total"] == 2
    assert d["subscriptions"]["by_status"] == {"ACTIVE": 1, "PENDING": 1}
    assert d["subscriptions"]["amount_pending"] == "3000.00"
    assert d["payments"]["total_collected"] == "3000.00"
    assert d["deliveries_today"]["total"] == 1
    assert d["meal_plans"][0]["active_subscriptions"] == 1


def test_owner_cannot_see_overview(mess):
    owner = User.objects.get(username="ov_owner")
    assert _get(owner, mess).status_code == 403


def test_business_list_counts_customers(super_admin, mess):
    client = APIClient()
    client.force_authenticate(super_admin)
    row = next(
        r
        for r in client.get("/api/v1/platform/businesses/").json()["results"]
        if r["name"] == "Overview Mess"
    )
    assert row["customer_count"] == 2
