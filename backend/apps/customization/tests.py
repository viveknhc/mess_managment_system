"""Customization tests — features, workflow policies, SUPER_ADMIN API, tenant isolation."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import serializers
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.customization.models import BusinessPolicy
from apps.customization.registry import (
    CUSTOMER_PORTAL,
    DEFAULT_FEATURES,
    EXTENSION_POINTS,
    ONLINE_PAYMENTS,
    REPORTS,
    SKIP,
    ExtensionPoint,
    Policy,
)
from apps.customization.services import FeatureService, PolicyService
from apps.deliveries.models import Delivery, DeliveryStatus, SkipAdjustment
from apps.deliveries.services import DeliveryService
from apps.meals.models import Meal
from apps.payments.services import OnlinePaymentService, PaymentService
from apps.plans.models import Plan
from apps.platform.models import SaasPlan, SaasSubscription
from apps.settings_app.models import BusinessSettings
from apps.subscriptions.services import SubscriptionService
from common.constants import Role

TODAY = timezone.localdate()


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
    return User.objects.create_user(username="root", password="pass", role=Role.SUPER_ADMIN)


@pytest.fixture()
def customer_user_a(biz_a):
    user = User.objects.create_user(username="cust_a", password="pass", role=Role.CUSTOMER, business=biz_a)
    Customer.objects.create(business=biz_a, name="Cust A", phone="9000000001", user=user)
    return user


@pytest.fixture()
def active_sub(biz_a):
    meal = Meal.objects.create(business=biz_a, name="Lunch")
    plan = Plan.objects.create(
        business=biz_a,
        name="Monthly",
        meal=meal,
        duration_days=30,
        total_meals=30,
        price=Decimal("3000.00"),
        skip_allowed=True,
    )
    customer = Customer.objects.create(business=biz_a, name="C", phone="9000000002")
    sub = SubscriptionService.create_subscription(
        business_id=biz_a.id, customer=customer, plan=plan, start_date=TODAY
    )
    PaymentService.record_payment(
        business_id=biz_a.id, subscription=sub, amount=plan.price, method="UPI", payment_date=TODAY
    )
    sub.refresh_from_db()
    return sub


def auth(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _plan_with(business, feature_keys):
    plan = SaasPlan.objects.create(name="Basic", price_monthly=Decimal("499.00"), feature_keys=feature_keys)
    SaasSubscription.objects.create(business=business, plan=plan)
    return plan


# ── Feature resolution ──────────────────────────────────────────────────


class TestFeatures:
    def test_no_plan_gets_default_features(self, biz_a):
        assert FeatureService.enabled(biz_a.id) == set(DEFAULT_FEATURES)

    def test_plan_without_feature_keys_gets_defaults(self, biz_a):
        _plan_with(biz_a, None)
        assert FeatureService.enabled(biz_a.id) == set(DEFAULT_FEATURES)

    def test_plan_feature_keys_limit_features(self, biz_a):
        _plan_with(biz_a, [REPORTS])
        assert FeatureService.enabled(biz_a.id) == {REPORTS}
        assert FeatureService.resolve(biz_a.id)[REPORTS] == (True, "plan")

    def test_override_beats_plan(self, biz_a):
        _plan_with(biz_a, [REPORTS])
        FeatureService.set_overrides(biz_a.id, {REPORTS: False, CUSTOMER_PORTAL: True})
        assert FeatureService.enabled(biz_a.id) == {CUSTOMER_PORTAL}
        assert FeatureService.resolve(biz_a.id)[CUSTOMER_PORTAL] == (True, "override")

    def test_clearing_override_returns_to_plan(self, biz_a):
        FeatureService.set_overrides(biz_a.id, {REPORTS: False})
        FeatureService.set_overrides(biz_a.id, {REPORTS: None})
        assert FeatureService.has(biz_a.id, REPORTS)

    def test_unknown_feature_rejected(self, biz_a):
        with pytest.raises(ValueError):
            FeatureService.set_overrides(biz_a.id, {"teleport": True})

    def test_no_business_has_no_features(self):
        assert FeatureService.enabled(None) == set()

    def test_override_is_per_business(self, biz_a, biz_b):
        FeatureService.set_overrides(biz_a.id, {REPORTS: False})
        assert not FeatureService.has(biz_a.id, REPORTS)
        assert FeatureService.has(biz_b.id, REPORTS)


# ── Feature gates on the API ────────────────────────────────────────────


class TestFeatureGates:
    def test_me_lists_features(self, owner_a, biz_a):
        FeatureService.set_overrides(biz_a.id, {REPORTS: False})
        features = auth(owner_a).get("/api/v1/auth/me/").json()["features"]
        assert REPORTS not in features
        assert CUSTOMER_PORTAL in features

    def test_reports_blocked_when_disabled(self, owner_a, biz_a):
        assert auth(owner_a).get("/api/v1/reports/customers/").status_code == 200
        FeatureService.set_overrides(biz_a.id, {REPORTS: False})
        resp = auth(owner_a).get("/api/v1/reports/customers/")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FEATURE_DISABLED"

    def test_reports_gate_only_affects_that_business(self, owner_a, owner_b, biz_a):
        FeatureService.set_overrides(biz_a.id, {REPORTS: False})
        assert auth(owner_b).get("/api/v1/reports/customers/").status_code == 200

    def test_portal_blocked_when_disabled(self, customer_user_a, biz_a):
        assert auth(customer_user_a).get("/api/v1/portal/dashboard/").status_code == 200
        FeatureService.set_overrides(biz_a.id, {CUSTOMER_PORTAL: False})
        resp = auth(customer_user_a).get("/api/v1/portal/dashboard/")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FEATURE_DISABLED"

    def test_online_payments_cannot_be_enabled_without_feature(self, owner_a, biz_a):
        FeatureService.set_overrides(biz_a.id, {ONLINE_PAYMENTS: False})
        resp = auth(owner_a).put(
            "/api/v1/settings/",
            {
                "razorpay_key_id": "rzp_test_abc",
                "razorpay_key_secret": "s3cret",
                "online_payments_enabled": True,
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "online_payments_enabled" in resp.json()["error"]["fields"]

    def test_online_payments_off_when_feature_removed(self, biz_a):
        s = BusinessSettings.objects.create(business=biz_a, razorpay_key_id="rzp_test_abc")
        s.set_razorpay_secret("s3cret")
        s.online_payments_enabled = True
        s.save()
        assert OnlinePaymentService.is_enabled(biz_a.id)
        FeatureService.set_overrides(biz_a.id, {ONLINE_PAYMENTS: False})
        assert not OnlinePaymentService.is_enabled(biz_a.id)

    def test_owner_can_still_save_settings_after_feature_removed(self, owner_a, biz_a):
        s = BusinessSettings.objects.create(business=biz_a, razorpay_key_id="rzp_test_abc")
        s.set_razorpay_secret("s3cret")
        s.online_payments_enabled = True
        s.save()
        FeatureService.set_overrides(biz_a.id, {ONLINE_PAYMENTS: False})
        resp = auth(owner_a).put(
            "/api/v1/settings/", {"online_payments_enabled": True, "max_pause_days": 4}, format="json"
        )
        assert resp.status_code == 200
        assert not OnlinePaymentService.is_enabled(biz_a.id)


# ── Workflow policies ───────────────────────────────────────────────────


def _tomorrow(sub):
    return Delivery.objects.get(subscription=sub, delivery_date=TODAY + timedelta(days=1))


class TestSkipPolicy:
    def test_default_is_no_adjustment(self, active_sub):
        end = active_sub.end_date
        skip = DeliveryService.skip_meal(_tomorrow(active_sub))
        active_sub.refresh_from_db()
        assert skip.adjustment == SkipAdjustment.NONE
        assert active_sub.end_date == end
        assert Delivery.objects.filter(subscription=active_sub, status=DeliveryStatus.PENDING).count() == 29

    def test_extend_pushes_end_date_and_replaces_meal(self, biz_a, active_sub):
        PolicyService.set_policy(biz_a.id, SKIP, "EXTEND")
        end = active_sub.end_date
        skip = DeliveryService.skip_meal(_tomorrow(active_sub))
        active_sub.refresh_from_db()
        assert skip.adjustment == SkipAdjustment.EXTEND
        assert active_sub.end_date == end + timedelta(days=1)
        assert Delivery.objects.filter(subscription=active_sub, status=DeliveryStatus.PENDING).count() == 30

    def test_extend_schedule_is_idempotent(self, biz_a, active_sub):
        PolicyService.set_policy(biz_a.id, SKIP, "EXTEND")
        DeliveryService.skip_meal(_tomorrow(active_sub))
        assert DeliveryService.generate_delivery_schedule(active_sub) == []

    def test_policy_is_per_business(self, biz_a, biz_b):
        PolicyService.set_policy(biz_a.id, SKIP, "EXTEND")
        assert PolicyService.get(biz_a.id, SKIP).key == "EXTEND"
        assert PolicyService.get(biz_b.id, SKIP).key == "NONE"

    def test_choosing_default_removes_row(self, biz_a):
        PolicyService.set_policy(biz_a.id, SKIP, "EXTEND")
        PolicyService.set_policy(biz_a.id, SKIP, "NONE")
        assert not BusinessPolicy.objects.filter(business=biz_a).exists()

    def test_unregistered_stored_policy_falls_back_to_default(self, biz_a):
        BusinessPolicy.objects.create(business=biz_a, point=SKIP, policy="REMOVED_LONG_AGO")
        assert PolicyService.get(biz_a.id, SKIP).key == "NONE"
        assert PolicyService.selected(biz_a.id)[SKIP] == ("NONE", {})

    def test_unknown_policy_rejected(self, biz_a):
        with pytest.raises(ValueError):
            PolicyService.set_policy(biz_a.id, SKIP, "TELEPORT")


class _CutoffParams(serializers.Serializer):
    hours = serializers.IntegerField(min_value=1, max_value=48, default=12)


@pytest.fixture()
def demo_point(monkeypatch):
    """A throwaway extension point with a params-taking policy."""
    point = ExtensionPoint("demo", "Demo", "Test only.", "PLAIN")

    @point.register
    class Plain(Policy):
        key = "PLAIN"
        label = "Plain"

    @point.register
    class Cutoff(Policy):
        key = "CUTOFF"
        label = "Cutoff"
        params_serializer = _CutoffParams

    monkeypatch.setitem(EXTENSION_POINTS, "demo", point)
    return point


class TestPolicyParams:
    def test_params_validated_and_passed_to_policy(self, biz_a, demo_point):
        PolicyService.set_policy(biz_a.id, "demo", "CUTOFF", {"hours": 6})
        assert PolicyService.get(biz_a.id, "demo").params == {"hours": 6}

    def test_params_defaults_applied(self, biz_a, demo_point):
        PolicyService.set_policy(biz_a.id, "demo", "CUTOFF", {})
        assert PolicyService.get(biz_a.id, "demo").params == {"hours": 12}

    def test_bad_params_rejected(self, biz_a, demo_point):
        with pytest.raises(serializers.ValidationError):
            PolicyService.set_policy(biz_a.id, "demo", "CUTOFF", {"hours": 99})

    def test_duplicate_registration_rejected(self, demo_point):
        with pytest.raises(ValueError):

            @demo_point.register
            class Again(Policy):
                key = "PLAIN"


# ── SUPER_ADMIN API ─────────────────────────────────────────────────────


def _url(business):
    return f"/api/v1/platform/businesses/{business.id}/customization/"


class TestCustomizationAPI:
    def test_catalog(self, super_admin):
        data = auth(super_admin).get("/api/v1/platform/customization/catalog/").json()
        assert {f["key"] for f in data["features"]} >= {CUSTOMER_PORTAL, ONLINE_PAYMENTS, REPORTS}
        skip = next(p for p in data["extension_points"] if p["key"] == SKIP)
        assert {p["key"] for p in skip["policies"]} == {"NONE", "EXTEND"}

    def test_catalog_describes_params(self, super_admin, demo_point):
        data = auth(super_admin).get("/api/v1/platform/customization/catalog/").json()
        demo = next(p for p in data["extension_points"] if p["key"] == "demo")
        cutoff = next(p for p in demo["policies"] if p["key"] == "CUTOFF")
        assert cutoff["params"] == [
            {"name": "hours", "type": "integer", "label": "Hours", "required": False, "default": 12}
        ]

    def test_get_business_customization(self, super_admin, biz_a):
        data = auth(super_admin).get(_url(biz_a)).json()
        assert {"key": REPORTS, "enabled": True, "source": "default", "inherited": True} in data["features"]
        assert {"point": SKIP, "policy": "NONE", "params": {}} in data["policies"]

    def test_update_features_and_policies(self, super_admin, biz_a):
        resp = auth(super_admin).put(
            _url(biz_a),
            {"features": {REPORTS: False}, "policies": {SKIP: {"policy": "EXTEND"}}},
            format="json",
        )
        assert resp.status_code == 200
        assert {"key": REPORTS, "enabled": False, "source": "override", "inherited": True} in resp.json()[
            "features"
        ]
        assert PolicyService.get(biz_a.id, SKIP).key == "EXTEND"
        log = AuditLog.objects.get(business_id=biz_a.id, action="CUSTOMIZE")
        assert log.user == super_admin
        assert "reports=off" in log.description and "skip=EXTEND" in log.description

    def test_unknown_feature_400(self, super_admin, biz_a):
        resp = auth(super_admin).put(_url(biz_a), {"features": {"teleport": True}}, format="json")
        assert resp.status_code == 400

    def test_unknown_policy_400(self, super_admin, biz_a):
        resp = auth(super_admin).put(_url(biz_a), {"policies": {SKIP: {"policy": "TELEPORT"}}}, format="json")
        assert resp.status_code == 400
        resp = auth(super_admin).put(_url(biz_a), {"policies": {"nope": {"policy": "X"}}}, format="json")
        assert resp.status_code == 400

    def test_bad_params_400(self, super_admin, biz_a, demo_point):
        resp = auth(super_admin).put(
            _url(biz_a), {"policies": {"demo": {"policy": "CUTOFF", "params": {"hours": 0}}}}, format="json"
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["fields"]["policies"]["demo"].startswith("Invalid settings — hours:")
        assert not BusinessPolicy.objects.filter(business=biz_a).exists()

    def test_owner_cannot_customize(self, owner_a, biz_a):
        assert auth(owner_a).get(_url(biz_a)).status_code == 403
        assert auth(owner_a).put(_url(biz_a), {"features": {REPORTS: True}}, format="json").status_code == 403
        assert auth(owner_a).get("/api/v1/platform/customization/catalog/").status_code == 403

    def test_unknown_business_404(self, super_admin, db):
        resp = auth(super_admin).get(
            "/api/v1/platform/businesses/00000000-0000-0000-0000-000000000000/customization/"
        )
        assert resp.status_code == 404

    def test_plan_feature_keys_validated(self, super_admin):
        base = {"name": "Pro", "price_monthly": "999.00"}
        resp = auth(super_admin).post(
            "/api/v1/platform/plans/", {**base, "feature_keys": ["teleport"]}, format="json"
        )
        assert resp.status_code == 400
        resp = auth(super_admin).post(
            "/api/v1/platform/plans/", {**base, "feature_keys": [REPORTS, REPORTS]}, format="json"
        )
        assert resp.status_code == 201
        assert resp.json()["feature_keys"] == [REPORTS]
