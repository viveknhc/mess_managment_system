"""Expiry email tests — EMAIL channel (owner digest + customer alerts)."""

import datetime
from datetime import timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.core import mail

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.meals.models import Meal
from apps.notifications.models import EmailLog, EmailStatus, Notification
from apps.notifications.services import NotificationService
from apps.notifications.tasks import send_expiring_notifications_task
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription
from common.constants import Role, SubStatus

TODAY = datetime.date.today()


@pytest.fixture(autouse=True)
def locmem_email(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "noreply@test.local"


def make_sub(biz, customer_name, end_date, *, email="", status=SubStatus.ACTIVE):
    meal = Meal.objects.create(business=biz, name=f"Lunch {customer_name}")
    plan = Plan.objects.create(
        business=biz,
        name=f"Weekly {customer_name}",
        meal=meal,
        duration_days=7,
        total_meals=7,
        price=Decimal("500.00"),
    )
    cust = Customer.objects.create(business=biz, name=customer_name, email=email)
    return Subscription.objects.create(
        business=biz,
        customer=cust,
        plan=plan,
        start_date=end_date - timedelta(days=7),
        end_date=end_date,
        status=status,
        total_amount=Decimal("500"),
        paid_amount=Decimal("500"),
        pending_amount=Decimal("0"),
        remaining_meals=2,
    )


@pytest.fixture()
def biz_a(db):
    return Business.objects.create(name="Mess A", email="mess-a@example.com")


@pytest.fixture()
def owner_a(biz_a):
    return User.objects.create_user(
        username="owner_a", password="pass", role=Role.OWNER, business=biz_a, email="owner-a@example.com"
    )


@pytest.fixture()
def biz_b(db):
    return Business.objects.create(name="Mess B", email="mess-b@example.com")


@pytest.fixture()
def owner_b(biz_b):
    return User.objects.create_user(
        username="owner_b", password="pass", role=Role.OWNER, business=biz_b, email="owner-b@example.com"
    )


def digests():
    return [m for m in mail.outbox if "digest" in m.subject]


@pytest.mark.django_db
class TestOwnerDigest:
    def test_digest_sent_to_business_and_owner(self, biz_a, owner_a):
        make_sub(biz_a, "Alice", TODAY + timedelta(days=2))
        make_sub(biz_a, "Carol", TODAY - timedelta(days=1), status=SubStatus.EXPIRED)

        NotificationService.send_expiry_emails(biz_a.id)

        [digest] = digests()
        assert set(digest.to) == {"mess-a@example.com", "owner-a@example.com"}
        assert "Mess A" in digest.subject
        assert "Alice" in digest.body and "Expiring in the next 3 days (1)" in digest.body
        assert "Carol" in digest.body and "Expired (1)" in digest.body
        assert digest.alternatives  # simple HTML alternative attached

    def test_only_owner_email_when_business_email_blank(self, db):
        biz = Business.objects.create(name="No Mail Mess")
        User.objects.create_user(username="o", password="p", role=Role.OWNER, business=biz, email="o@x.com")
        User.objects.create_user(
            username="d", password="p", role=Role.DELIVERY_STAFF, business=biz, email="staff@x.com"
        )
        make_sub(biz, "Alice", TODAY + timedelta(days=1))

        NotificationService.send_expiry_emails(biz.id)

        [digest] = digests()
        assert digest.to == ["o@x.com"]

    def test_no_digest_when_nothing_expiring(self, biz_a, owner_a):
        make_sub(biz_a, "Far", TODAY + timedelta(days=20))
        assert NotificationService.send_expiry_emails(biz_a.id) == 0
        assert mail.outbox == []

    def test_respects_notify_on_expiring_setting(self, biz_a, owner_a):
        from apps.settings_app.models import BusinessSettings

        BusinessSettings.objects.create(business=biz_a, notify_on_expiring=False)
        make_sub(biz_a, "Alice", TODAY + timedelta(days=2), email="alice@example.com")
        assert NotificationService.send_expiry_emails(biz_a.id) == 0
        assert mail.outbox == []


@pytest.mark.django_db
class TestCustomerEmail:
    def test_customer_with_email_gets_alert(self, biz_a, owner_a):
        make_sub(biz_a, "Alice", TODAY + timedelta(days=2), email="alice@example.com")

        NotificationService.send_expiry_emails(biz_a.id)

        cust_mails = [m for m in mail.outbox if m.to == ["alice@example.com"]]
        assert len(cust_mails) == 1
        assert "Mess A" in cust_mails[0].subject
        assert "expires on" in cust_mails[0].body

    def test_no_email_when_nobody_has_email(self, db):
        biz = Business.objects.create(name="Silent Mess")
        User.objects.create_user(username="o2", password="p", role=Role.OWNER, business=biz)
        make_sub(biz, "Alice", TODAY + timedelta(days=2))

        assert NotificationService.send_expiry_emails(biz.id) == 0
        assert mail.outbox == []
        assert not EmailLog.objects.exists()


@pytest.mark.django_db
class TestIdempotencyAndFailures:
    def test_no_duplicate_on_second_run(self, biz_a, owner_a):
        make_sub(biz_a, "Alice", TODAY + timedelta(days=2), email="alice@example.com")

        send_expiring_notifications_task()
        first = len(mail.outbox)
        send_expiring_notifications_task()

        assert first == 2  # digest + customer
        assert len(mail.outbox) == first
        assert EmailLog.objects.filter(status=EmailStatus.SENT).count() == 2

    def test_failed_send_is_logged_and_retried(self, biz_a, owner_a):
        make_sub(biz_a, "Alice", TODAY + timedelta(days=2))
        with mock.patch(
            "apps.notifications.services.EmailMultiAlternatives.send", side_effect=OSError("smtp down")
        ):
            assert NotificationService.send_expiry_emails(biz_a.id) == 0
        log = EmailLog.objects.get(business=biz_a)
        assert log.status == EmailStatus.FAILED and "smtp down" in log.error

        # Next run retries the failed send
        assert NotificationService.send_expiry_emails(biz_a.id) == 1
        assert EmailLog.objects.get(business=biz_a).status == EmailStatus.SENT

    def test_one_business_send_failure_does_not_stop_others(self, biz_a, owner_a, biz_b, owner_b):
        make_sub(biz_a, "Alice", TODAY + timedelta(days=2))
        make_sub(biz_b, "Bob", TODAY + timedelta(days=2))

        from django.core.mail import EmailMultiAlternatives

        real_send = EmailMultiAlternatives.send

        def flaky_send(self, *args, **kwargs):
            if "Mess A" in self.subject:
                raise OSError("smtp down for A")
            return real_send(self, *args, **kwargs)

        with mock.patch.object(EmailMultiAlternatives, "send", flaky_send):
            send_expiring_notifications_task()

        assert [m.subject for m in digests()] == [f"[Mess B] Subscription expiry digest — {TODAY}"]
        assert EmailLog.objects.get(business=biz_a).status == EmailStatus.FAILED

    def test_one_business_crash_does_not_stop_others(self, biz_a, owner_a, biz_b, owner_b):
        make_sub(biz_a, "Alice", TODAY + timedelta(days=2))
        make_sub(biz_b, "Bob", TODAY + timedelta(days=2))

        real = NotificationService.send_expiry_emails

        def crash_for_a(business_id):
            if business_id == biz_a.id:
                raise RuntimeError("boom")
            return real(business_id)

        with mock.patch.object(NotificationService, "send_expiry_emails", side_effect=crash_for_a):
            send_expiring_notifications_task()

        assert len(digests()) == 1
        assert "Mess B" in digests()[0].subject
        # In-app notifications still created for both businesses
        assert Notification.objects.filter(business=biz_a).count() == 1
        assert Notification.objects.filter(business=biz_b).count() == 1


@pytest.mark.django_db
class TestTenantIsolation:
    def test_digest_never_lists_other_business_customers(self, biz_a, owner_a, biz_b, owner_b):
        make_sub(biz_a, "AliceOfA", TODAY + timedelta(days=1), email="alice@example.com")
        make_sub(biz_b, "BobOfB", TODAY + timedelta(days=1), email="bob@example.com")
        make_sub(biz_b, "CarlOfB", TODAY - timedelta(days=1), status=SubStatus.EXPIRED)

        NotificationService.send_expiry_emails(biz_a.id)

        assert {tuple(m.to) for m in mail.outbox} == {
            ("mess-a@example.com", "owner-a@example.com"),
            ("alice@example.com",),
        }
        for m in mail.outbox:
            assert "BobOfB" not in m.body and "CarlOfB" not in m.body
            assert "Mess B" not in m.body
            assert "owner-b@example.com" not in m.to
