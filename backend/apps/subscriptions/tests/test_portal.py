"""Customer portal permission, isolation, and action tests (PT-02). Hard rule #1."""

import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.deliveries.models import Delivery, DeliveryStatus
from apps.meals.models import Meal
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription
from common.constants import Role, SubStatus

D = datetime.date.today


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture()
def biz_a(db):
    return Business.objects.create(name="Portal Mess A")


@pytest.fixture()
def biz_b(db):
    return Business.objects.create(name="Portal Mess B")


@pytest.fixture()
def cust_user_a(biz_a):
    return User.objects.create_user(username="cust_a", password="pass", role=Role.CUSTOMER, business=biz_a)


@pytest.fixture()
def cust_user_b(biz_b):
    return User.objects.create_user(username="cust_b", password="pass", role=Role.CUSTOMER, business=biz_b)


@pytest.fixture()
def owner_a(biz_a):
    return User.objects.create_user(
        username="portal_owner_a", password="pass", role=Role.OWNER, business=biz_a
    )


@pytest.fixture()
def staff_a(biz_a):
    return User.objects.create_user(
        username="portal_staff_a", password="pass", role=Role.DELIVERY_STAFF, business=biz_a
    )


@pytest.fixture()
def customer_a(biz_a, cust_user_a):
    return Customer.objects.create(business=biz_a, user=cust_user_a, name="Alice Portal", phone="9990000001")


@pytest.fixture()
def customer_a2(biz_a):
    """Second customer in the SAME business, with own portal user."""
    user = User.objects.create_user(username="cust_a2", password="pass", role=Role.CUSTOMER, business=biz_a)
    return Customer.objects.create(business=biz_a, user=user, name="Bob SameBiz", phone="9990000002")


@pytest.fixture()
def customer_b(biz_b, cust_user_b):
    return Customer.objects.create(business=biz_b, user=cust_user_b, name="Charlie Other", phone="9990000003")


@pytest.fixture()
def meal_a(biz_a):
    return Meal.objects.create(business=biz_a, name="Lunch")


@pytest.fixture()
def plan_a(biz_a, meal_a):
    return Plan.objects.create(
        business=biz_a,
        name="Monthly Lunch",
        meal=meal_a,
        duration_days=30,
        total_meals=30,
        price=Decimal("2500.00"),
        skip_allowed=True,
        pause_allowed=True,
    )


@pytest.fixture()
def sub_a(biz_a, customer_a, plan_a):
    return Subscription.objects.create(
        business=biz_a,
        customer=customer_a,
        plan=plan_a,
        start_date=D(),
        end_date=D() + datetime.timedelta(days=30),
        status=SubStatus.ACTIVE,
        total_amount=Decimal("2500.00"),
        paid_amount=Decimal("2500.00"),
        pending_amount=Decimal("0.00"),
        remaining_meals=30,
    )


@pytest.fixture()
def sub_a2(biz_a, customer_a2, plan_a):
    return Subscription.objects.create(
        business=biz_a,
        customer=customer_a2,
        plan=plan_a,
        start_date=D(),
        end_date=D() + datetime.timedelta(days=30),
        status=SubStatus.ACTIVE,
        total_amount=Decimal("2500.00"),
        paid_amount=Decimal("2500.00"),
        pending_amount=Decimal("0.00"),
        remaining_meals=30,
    )


@pytest.fixture()
def sub_b(biz_b, customer_b, plan_a):
    return Subscription.objects.create(
        business=biz_b,
        customer=customer_b,
        plan=plan_a,
        start_date=D(),
        end_date=D() + datetime.timedelta(days=30),
        status=SubStatus.ACTIVE,
        total_amount=Decimal("2500.00"),
        paid_amount=Decimal("2500.00"),
        pending_amount=Decimal("0.00"),
        remaining_meals=30,
    )


@pytest.fixture()
def today_delivery(sub_a):
    return Delivery.objects.create(
        business=sub_a.business,
        subscription=sub_a,
        customer=sub_a.customer,
        meal=sub_a.plan.meal,
        delivery_date=D(),
        status=DeliveryStatus.PENDING,
    )


def client_for(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ── PT-02: permission & isolation ────────────────────────────────────────


@pytest.mark.django_db
class TestPortalPermissions:
    def test_owner_cannot_access_portal(self, owner_a, customer_a):
        resp = client_for(owner_a).get("/api/v1/portal/dashboard/")
        assert resp.status_code == 403

    def test_staff_cannot_access_portal(self, staff_a):
        resp = client_for(staff_a).get("/api/v1/portal/dashboard/")
        assert resp.status_code == 403

    def test_customer_without_profile_gets_404(self, biz_a):
        user = User.objects.create_user(
            username="cust_noprofile", password="pass", role=Role.CUSTOMER, business=biz_a
        )
        resp = client_for(user).get("/api/v1/portal/dashboard/")
        assert resp.status_code == 404

    def test_unauthenticated_gets_401(self):
        resp = APIClient().get("/api/v1/portal/dashboard/")
        assert resp.status_code == 401


@pytest.mark.django_db
class TestPortalSelfScoping:
    def test_dashboard_shows_only_own_data(self, cust_user_a, customer_a, sub_a):
        resp = client_for(cust_user_a).get("/api/v1/portal/dashboard/")
        assert resp.status_code == 200
        assert resp.json()["customer_name"] == "Alice Portal"
        assert resp.json()["active_subscription"]["id"] == str(sub_a.id)

    def test_subscriptions_list_excludes_same_business_other_customer(self, cust_user_a, sub_a, sub_a2):
        """Customer of Business A must not see another customer in the SAME business."""
        resp = client_for(cust_user_a).get("/api/v1/portal/subscriptions/")
        ids = {s["id"] for s in resp.json()}
        assert str(sub_a.id) in ids
        assert str(sub_a2.id) not in ids

    def test_payments_self_only(self, cust_user_a, customer_a, sub_a):
        from apps.payments.models import Payment

        Payment.objects.create(
            business=customer_a.business,
            customer=customer_a,
            subscription=sub_a,
            amount=Decimal("100.00"),
            method="CASH",
            payment_date=D(),
            status="PAID",
        )
        resp = client_for(cust_user_a).get("/api/v1/portal/payments/")
        assert resp.status_code == 200
        assert all(p["customer"] == str(customer_a.id) for p in resp.json())

    def test_deliveries_self_only(self, cust_user_a, sub_a, sub_a2):
        resp = client_for(cust_user_a).get("/api/v1/portal/deliveries/")
        assert resp.status_code == 200
        assert all(d["customer"] == str(sub_a.customer.id) for d in resp.json())

    def test_cross_business_subscription_is_404(self, cust_user_a, sub_b):
        """Customer of Business A gets 404 (not 403) on Business B subscription actions."""
        resp = client_for(cust_user_a).post(f"/api/v1/portal/subscriptions/{sub_b.id}/renew/")
        assert resp.status_code == 404

    def test_same_business_other_customer_subscription_is_404(self, cust_user_a, sub_a2):
        resp = client_for(cust_user_a).post(f"/api/v1/portal/subscriptions/{sub_a2.id}/renew/")
        assert resp.status_code == 404

    def test_customer_cannot_list_admin_customers(self, cust_user_a):
        resp = client_for(cust_user_a).get("/api/v1/customers/")
        assert resp.status_code in (403, 404)

    def test_customer_cannot_create_subscription_via_admin_api(self, cust_user_a, customer_a, plan_a):
        resp = client_for(cust_user_a).post(
            "/api/v1/subscriptions/",
            {"customer": str(customer_a.id), "plan": str(plan_a.id)},
            format="json",
        )
        assert resp.status_code in (403, 404)

    def test_customer_cannot_update_delivery_status(self, cust_user_a, today_delivery):
        resp = client_for(cust_user_a).patch(
            f"/api/v1/deliveries/{today_delivery.id}/status/", {"status": "DELIVERED"}, format="json"
        )
        assert resp.status_code in (403, 404)


# ── PT-03: dashboard payload ─────────────────────────────────────────────


@pytest.mark.django_db
class TestPortalDashboard:
    def test_todays_meal_status(self, cust_user_a, today_delivery):
        resp = client_for(cust_user_a).get("/api/v1/portal/dashboard/")
        meal = resp.json()["todays_meal"]
        assert meal["meal_name"] == "Lunch"
        assert meal["status"] == "PENDING"
        assert meal["skippable"] is True

    def test_no_active_subscription(self, cust_user_a, customer_a):
        resp = client_for(cust_user_a).get("/api/v1/portal/dashboard/")
        assert resp.json()["active_subscription"] is None
        assert resp.json()["todays_meal"] is None


# ── Portal actions: skip / pause-request / renew ─────────────────────────


@pytest.mark.django_db
class TestPortalSkip:
    def test_skip_todays_meal(self, cust_user_a, sub_a, today_delivery):
        resp = client_for(cust_user_a).post(
            f"/api/v1/portal/subscriptions/{sub_a.id}/skip/", {"reason": "Going home"}, format="json"
        )
        assert resp.status_code == 200
        today_delivery.refresh_from_db()
        assert today_delivery.status == DeliveryStatus.SKIPPED

    def test_skip_specific_future_date(self, cust_user_a, sub_a):
        Delivery.objects.create(
            business=sub_a.business,
            subscription=sub_a,
            customer=sub_a.customer,
            meal=sub_a.plan.meal,
            delivery_date=D() + datetime.timedelta(days=2),
            status=DeliveryStatus.PENDING,
        )
        target = D() + datetime.timedelta(days=2)
        resp = client_for(cust_user_a).post(
            f"/api/v1/portal/subscriptions/{sub_a.id}/skip/", {"date": str(target)}, format="json"
        )
        assert resp.status_code == 200
        assert resp.json()["skip_date"] == str(target)

    def test_skip_past_date_rejected(self, cust_user_a, sub_a):
        resp = client_for(cust_user_a).post(
            f"/api/v1/portal/subscriptions/{sub_a.id}/skip/",
            {"date": str(D() - datetime.timedelta(days=1))},
            format="json",
        )
        assert resp.status_code == 400

    def test_skip_when_no_pending_delivery(self, cust_user_a, sub_a):
        resp = client_for(cust_user_a).post(
            f"/api/v1/portal/subscriptions/{sub_a.id}/skip/", {}, format="json"
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.django_db
class TestPortalPause:
    def test_pause_request_cancels_deliveries(self, cust_user_a, sub_a):
        Delivery.objects.create(
            business=sub_a.business,
            subscription=sub_a,
            customer=sub_a.customer,
            meal=sub_a.plan.meal,
            delivery_date=D() + datetime.timedelta(days=1),
            status=DeliveryStatus.PENDING,
        )
        start = D() + datetime.timedelta(days=1)
        resp = client_for(cust_user_a).post(
            f"/api/v1/portal/subscriptions/{sub_a.id}/pause-request/",
            {"start_date": str(start), "end_date": str(start), "reason": "travel"},
            format="json",
        )
        assert resp.status_code == 200
        sub_a.refresh_from_db()
        assert sub_a.status == SubStatus.PAUSED
        d = Delivery.objects.get(subscription=sub_a, delivery_date=start)
        assert d.status == DeliveryStatus.CANCELLED

    def test_pause_min_duration_enforced(self, cust_user_a, sub_a, biz_a):
        from apps.settings_app.models import BusinessSettings

        BusinessSettings.objects.create(business=biz_a, min_pause_days=2)
        start = D() + datetime.timedelta(days=1)
        resp = client_for(cust_user_a).post(
            f"/api/v1/portal/subscriptions/{sub_a.id}/pause-request/",
            {"start_date": str(start), "end_date": str(start)},
            format="json",
        )
        assert resp.status_code == 400

    def test_pause_max_duration_enforced(self, cust_user_a, sub_a, biz_a):
        from apps.settings_app.models import BusinessSettings

        BusinessSettings.objects.create(business=biz_a, max_pause_days=3)
        start = D() + datetime.timedelta(days=1)
        resp = client_for(cust_user_a).post(
            f"/api/v1/portal/subscriptions/{sub_a.id}/pause-request/",
            {
                "start_date": str(start),
                "end_date": str(start + datetime.timedelta(days=9)),
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_pause_start_in_past_rejected(self, cust_user_a, sub_a):
        resp = client_for(cust_user_a).post(
            f"/api/v1/portal/subscriptions/{sub_a.id}/pause-request/",
            {"start_date": str(D() - datetime.timedelta(days=1))},
            format="json",
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestPortalRenew:
    def test_renew_expired_subscription(self, cust_user_a, sub_a):
        sub_a.status = SubStatus.EXPIRED
        sub_a.save()
        resp = client_for(cust_user_a).post(f"/api/v1/portal/subscriptions/{sub_a.id}/renew/")
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == SubStatus.PENDING
        assert body["renewed_from"] == str(sub_a.id)

    def test_renew_active_rejected(self, cust_user_a, sub_a):
        resp = client_for(cust_user_a).post(f"/api/v1/portal/subscriptions/{sub_a.id}/renew/")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


# ── PT-06: profile ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPortalProfile:
    def test_get_profile(self, cust_user_a, customer_a):
        resp = client_for(cust_user_a).get("/api/v1/portal/profile/")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Alice Portal"

    def test_edit_limited_fields(self, cust_user_a, customer_a):
        resp = client_for(cust_user_a).put(
            "/api/v1/portal/profile/",
            {"phone": "9888888888", "address": "New Address 42"},
            format="json",
        )
        assert resp.status_code == 200
        customer_a.refresh_from_db()
        assert customer_a.phone == "9888888888"
        assert customer_a.address == "New Address 42"

    def test_cannot_edit_name_or_status(self, cust_user_a, customer_a):
        resp = client_for(cust_user_a).put(
            "/api/v1/portal/profile/",
            {"name": "Hacked Name", "status": "BLOCKED"},
            format="json",
        )
        assert resp.status_code == 200
        customer_a.refresh_from_db()
        assert customer_a.name == "Alice Portal"
        assert customer_a.status == "ACTIVE"
