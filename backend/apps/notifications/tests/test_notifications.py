"""Notification tests (N-06)."""

import datetime
from datetime import timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.meals.models import Meal
from apps.notifications.models import Notification, NotificationType
from apps.notifications.services import NotificationService
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription
from common.constants import Role, SubStatus

TODAY = datetime.date.today()


@pytest.fixture()
def biz_a(db):
    return Business.objects.create(name="Mess A")


@pytest.fixture()
def owner_a(biz_a):
    return User.objects.create_user(username="owner_a", password="pass", role=Role.OWNER, business=biz_a)


@pytest.fixture()
def owner_a2(biz_a):
    return User.objects.create_user(username="owner_a2", password="pass", role=Role.OWNER, business=biz_a)


@pytest.fixture()
def delivery_a(biz_a):
    return User.objects.create_user(
        username="delivery_a", password="pass", role=Role.DELIVERY_STAFF, business=biz_a
    )


@pytest.fixture()
def biz_b(db):
    return Business.objects.create(name="Mess B")


@pytest.fixture()
def owner_b(biz_b):
    return User.objects.create_user(username="owner_b", password="pass", role=Role.OWNER, business=biz_b)


@pytest.fixture()
def expiring_sub(biz_a):
    meal = Meal.objects.create(business=biz_a, name="Lunch")
    plan = Plan.objects.create(
        business=biz_a, name="Weekly", meal=meal, duration_days=7, total_meals=7, price=Decimal("500.00")
    )
    cust = Customer.objects.create(business=biz_a, name="Alice")
    return Subscription.objects.create(
        business=biz_a,
        customer=cust,
        plan=plan,
        start_date=TODAY - timedelta(days=5),
        end_date=TODAY + timedelta(days=2),
        status=SubStatus.ACTIVE,
        total_amount=Decimal("500"),
        paid_amount=Decimal("500"),
        pending_amount=Decimal("0"),
        remaining_meals=2,
    )


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


URL = "/api/v1/notifications/"


# ── Service: emit ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestNotificationEmit:
    def test_emit_creates_notification(self, biz_a, owner_a):
        notif = NotificationService.emit(
            business_id=biz_a.id,
            user=owner_a,
            notification_type=NotificationType.GENERAL,
            title="Test",
            message="Hello",
        )
        assert notif.is_read is False
        assert Notification.objects.filter(user=owner_a).count() == 1

    def test_emit_payment_received(self, biz_a, owner_a):
        notif = NotificationService.emit_payment_received(
            business_id=biz_a.id, user=owner_a, amount=Decimal("500"), customer_name="Alice"
        )
        assert notif.type == NotificationType.PAYMENT_RECEIVED
        assert "500" in notif.message

    def test_emit_subscription_activated(self, biz_a, owner_a):
        notif = NotificationService.emit_subscription_activated(
            business_id=biz_a.id, user=owner_a, customer_name="Alice", plan_name="Weekly"
        )
        assert notif.type == NotificationType.SUBSCRIPTION_ACTIVATED


# ── Service: expiring notifications (N-04) ───────────────────────────────


@pytest.mark.django_db
class TestExpiringNotifications:
    def test_sends_to_owners(self, biz_a, owner_a, expiring_sub):
        count = NotificationService.emit_expiring_notifications(biz_a.id)
        assert count == 1
        notif = Notification.objects.filter(user=owner_a).first()
        assert notif.type == NotificationType.SUBSCRIPTION_EXPIRING

    def test_sends_to_all_owners(self, biz_a, owner_a, owner_a2, expiring_sub):
        count = NotificationService.emit_expiring_notifications(biz_a.id)
        assert count == 2

    def test_no_duplicates_same_day(self, biz_a, owner_a, expiring_sub):
        NotificationService.emit_expiring_notifications(biz_a.id)
        count = NotificationService.emit_expiring_notifications(biz_a.id)
        assert count == 0

    def test_no_notification_for_far_future(self, biz_a, owner_a):
        """Active sub with end_date far away should not trigger."""
        meal = Meal.objects.create(business=biz_a, name="Dinner")
        plan = Plan.objects.create(
            business=biz_a, name="Monthly", meal=meal, duration_days=30, total_meals=30, price=Decimal("2500")
        )
        cust = Customer.objects.create(business=biz_a, name="Bob")
        Subscription.objects.create(
            business=biz_a,
            customer=cust,
            plan=plan,
            start_date=TODAY,
            end_date=TODAY + timedelta(days=30),
            status=SubStatus.ACTIVE,
            total_amount=Decimal("2500"),
            paid_amount=Decimal("2500"),
            pending_amount=Decimal("0"),
            remaining_meals=30,
        )
        count = NotificationService.emit_expiring_notifications(biz_a.id)
        assert count == 0


# ── API endpoints (N-05) ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestNotificationAPI:
    def test_list_own_notifications(self, owner_a, biz_a):
        NotificationService.emit(
            business_id=biz_a.id,
            user=owner_a,
            notification_type=NotificationType.GENERAL,
            title="Test",
            message="Hello",
        )
        resp = auth_client(owner_a).get(URL)
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_unread_count(self, owner_a, biz_a):
        NotificationService.emit(
            business_id=biz_a.id,
            user=owner_a,
            notification_type=NotificationType.GENERAL,
            title="Test",
            message="Hello",
        )
        resp = auth_client(owner_a).get(f"{URL}unread_count/")
        assert resp.json()["unread_count"] == 1

    def test_mark_read(self, owner_a, biz_a):
        notif = NotificationService.emit(
            business_id=biz_a.id,
            user=owner_a,
            notification_type=NotificationType.GENERAL,
            title="Test",
            message="Hello",
        )
        resp = auth_client(owner_a).post(f"{URL}{notif.id}/mark_read/")
        assert resp.status_code == 200
        assert resp.json()["is_read"] is True

    def test_mark_all_read(self, owner_a, biz_a):
        for i in range(3):
            NotificationService.emit(
                business_id=biz_a.id,
                user=owner_a,
                notification_type=NotificationType.GENERAL,
                title=f"Test {i}",
                message="Hello",
            )
        resp = auth_client(owner_a).post(f"{URL}mark_all_read/")
        assert resp.json()["marked_read"] == 3

    def test_scoping_user_a_cannot_see_user_b(self, owner_a, owner_b, biz_a, biz_b):
        NotificationService.emit(
            business_id=biz_b.id,
            user=owner_b,
            notification_type=NotificationType.GENERAL,
            title="B's notif",
            message="Secret",
        )
        resp = auth_client(owner_a).get(URL)
        assert resp.json()["count"] == 0

    def test_unauthenticated_rejected(self, db):
        resp = APIClient().get(URL)
        assert resp.status_code == 401
