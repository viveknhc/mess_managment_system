# ruff: noqa: F811 — fixtures imported from test_portal are injected by name
"""Regression tests for the low-severity audit fixes.

L1 back-to-back pauses · L3 meals left · L4 kitchen staff and customer data ·
L5 dashboard today count · L6 expiry alerts setting · L7 last owner ·
L9 portal profile · L12 username case · pause settings sanity.
(L2 is a row lock, L8/L10 are covered in platform and auth tests, L11 is frontend.)
"""

import datetime
from datetime import timedelta

import pytest

from apps.accounts.models import User
from apps.deliveries.models import Delivery, DeliveryStatus
from apps.deliveries.services import DeliveryService
from apps.notifications.services import NotificationService
from apps.settings_app.models import BusinessSettings
from apps.subscriptions.services import SubscriptionService
from apps.subscriptions.tests.test_portal import (  # noqa: F401 — pytest fixtures
    biz_a,
    client_for,
    cust_user_a,
    customer_a,
    meal_a,
    owner_a,
    plan_a,
    sub_a,
)
from common.constants import Role

TODAY = datetime.date.today()


def _settings(business, **values):
    BusinessSettings.objects.update_or_create(business=business, defaults=values)


def _pause(user, sub, start, end):
    return client_for(user).post(
        f"/api/v1/portal/subscriptions/{sub.id}/pause-request/",
        {"start_date": str(start), "end_date": str(end)},
        format="json",
    )


# ── L1: back-to-back pauses count as one ──────────────────────────────────


@pytest.mark.django_db
class TestPausesInARow:
    def test_chained_pause_over_limit_refused(self, cust_user_a, sub_a):
        _settings(sub_a.business, max_pause_days=3, min_pause_days=1)
        t = TODAY + timedelta(days=1)
        assert _pause(cust_user_a, sub_a, t, t + timedelta(days=2)).status_code == 200
        resp = _pause(cust_user_a, sub_a, t + timedelta(days=3), t + timedelta(days=4))
        assert resp.status_code == 400
        assert "back to back" in resp.json()["error"]["message"]

    def test_chain_joining_from_before_refused(self, cust_user_a, sub_a):
        _settings(sub_a.business, max_pause_days=3, min_pause_days=1)
        t = TODAY + timedelta(days=4)
        assert _pause(cust_user_a, sub_a, t, t + timedelta(days=1)).status_code == 200
        assert _pause(cust_user_a, sub_a, t - timedelta(days=2), t - timedelta(days=1)).status_code == 400

    def test_pause_after_a_gap_day_allowed(self, cust_user_a, sub_a):
        _settings(sub_a.business, max_pause_days=3, min_pause_days=1)
        t = TODAY + timedelta(days=1)
        assert _pause(cust_user_a, sub_a, t, t + timedelta(days=2)).status_code == 200
        assert _pause(cust_user_a, sub_a, t + timedelta(days=4), t + timedelta(days=5)).status_code == 200

    def test_min_pause_cannot_exceed_max(self, owner_a, biz_a):
        resp = client_for(owner_a).put(
            "/api/v1/settings/", {"min_pause_days": 5, "max_pause_days": 2}, format="json"
        )
        assert resp.status_code == 400


# ── L3: meals left stays true ─────────────────────────────────────────────


@pytest.fixture()
def scheduled(sub_a):
    DeliveryService.generate_delivery_schedule(sub_a)
    sub_a.refresh_from_db()
    return sub_a


@pytest.mark.django_db
class TestMealsLeft:
    def test_delivered_meal_counts_down(self, scheduled):
        today = Delivery.objects.get(subscription=scheduled, delivery_date=TODAY)
        DeliveryService.update_status(today, DeliveryStatus.DELIVERED)
        scheduled.refresh_from_db()
        assert scheduled.remaining_meals == 29

    def test_undo_counts_back_up(self, scheduled):
        today = Delivery.objects.get(subscription=scheduled, delivery_date=TODAY)
        DeliveryService.update_status(today, DeliveryStatus.DELIVERED)
        DeliveryService.undo_status(today)
        scheduled.refresh_from_db()
        assert scheduled.remaining_meals == 30

    def test_cancelled_owes_nothing(self, scheduled):
        SubscriptionService.cancel(scheduled)
        scheduled.refresh_from_db()
        assert scheduled.remaining_meals == 0


# ── L4: kitchen staff see counts, not customer details ────────────────────


@pytest.fixture()
def kitchen(biz_a):
    return User.objects.create_user(
        username="kitchen", password="pass", role=Role.KITCHEN_STAFF, business=biz_a
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url,code",
    [
        ("/api/v1/deliveries/", 403),
        ("/api/v1/customers/", 403),
        ("/api/v1/payments/", 403),
        ("/api/v1/subscriptions/", 403),
        ("/api/v1/deliveries/kitchen_counts/", 200),
        ("/api/v1/deliveries/today_summary/", 200),
    ],
)
def test_kitchen_staff_access(kitchen, url, code):
    assert client_for(kitchen).get(url).status_code == code


# ── L5: dashboard counts today's work like the delivery screens ──────────


@pytest.mark.django_db
def test_dashboard_today_excludes_paused(owner_a, scheduled):
    before = client_for(owner_a).get("/api/v1/dashboard/").json()["deliveries"]["total_today"]
    SubscriptionService.pause(scheduled, start_date=TODAY, end_date=TODAY + timedelta(days=1))
    after = client_for(owner_a).get("/api/v1/dashboard/").json()["deliveries"]["total_today"]
    assert (before, after) == (1, 0)


# ── L6: expiry alerts follow the owner's setting ──────────────────────────


@pytest.mark.django_db
def test_in_app_expiry_alerts_respect_setting(owner_a, sub_a):
    sub_a.end_date = TODAY + timedelta(days=2)
    sub_a.save(update_fields=["end_date"])
    _settings(sub_a.business, notify_on_expiring=False)
    assert NotificationService.emit_expiring_notifications(sub_a.business_id) == 0
    _settings(sub_a.business, notify_on_expiring=True)
    assert NotificationService.emit_expiring_notifications(sub_a.business_id) == 1


# ── L7: there's always an active owner ────────────────────────────────────


@pytest.fixture()
def owner_b2(biz_a):
    return User.objects.create_user(username="owner_two", password="pass", role=Role.OWNER, business=biz_a)


@pytest.mark.django_db
class TestLastOwner:
    """Simulates the race: by the time A's request runs, A was already deactivated by B."""

    def _a_already_gone(self, owner_a):
        User.objects.filter(pk=owner_a.pk).update(is_active=False)

    def test_patch_is_active_refused(self, owner_a, owner_b2):
        self._a_already_gone(owner_a)
        resp = client_for(owner_a).patch(f"/api/v1/staff/{owner_b2.id}/", {"is_active": False}, format="json")
        assert resp.status_code == 400
        owner_b2.refresh_from_db()
        assert owner_b2.is_active

    @pytest.mark.parametrize("how", ["deactivate", "destroy"])
    def test_deactivate_and_delete_refused(self, owner_a, owner_b2, how):
        self._a_already_gone(owner_a)
        api = client_for(owner_a)
        url = f"/api/v1/staff/{owner_b2.id}/"
        resp = api.post(f"{url}deactivate/") if how == "deactivate" else api.delete(url)
        assert resp.status_code == 400
        owner_b2.refresh_from_db()
        assert owner_b2.is_active

    def test_with_another_owner_left_it_works(self, owner_a, owner_b2):
        resp = client_for(owner_a).post(f"/api/v1/staff/{owner_b2.id}/deactivate/")
        assert resp.status_code == 200


# ── L9: portal profile validation ─────────────────────────────────────────

PROFILE = "/api/v1/portal/profile/"


@pytest.mark.django_db
class TestPortalProfile:
    def test_too_long_phone_rejected_not_500(self, cust_user_a, customer_a):
        resp = client_for(cust_user_a).put(PROFILE, {"phone": "9" * 40}, format="json")
        assert resp.status_code == 400

    def test_bad_email_rejected(self, cust_user_a, customer_a):
        assert (
            client_for(cust_user_a).put(PROFILE, {"email": "not-an-email"}, format="json").status_code == 400
        )

    def test_email_change_reaches_login(self, cust_user_a, customer_a):
        resp = client_for(cust_user_a).put(PROFILE, {"email": "new@example.com"}, format="json")
        assert resp.status_code == 200
        cust_user_a.refresh_from_db()
        assert cust_user_a.email == "new@example.com"

    def test_phone_of_another_customer_rejected(self, biz_a, cust_user_a, customer_a):
        from apps.customers.models import Customer

        Customer.objects.create(business=biz_a, name="Other", phone="9123456780")
        assert client_for(cust_user_a).put(PROFILE, {"phone": "9123456780"}, format="json").status_code == 400


# ── L12: usernames unique regardless of case ──────────────────────────────


@pytest.mark.django_db
def test_staff_username_case_insensitive(owner_a):
    resp = client_for(owner_a).post(
        "/api/v1/staff/",
        {
            "username": owner_a.username.upper(),
            "password": "staffpass123",
            "name": "Dup",
            "role": Role.MANAGER,
        },
        format="json",
    )
    assert resp.status_code == 400
