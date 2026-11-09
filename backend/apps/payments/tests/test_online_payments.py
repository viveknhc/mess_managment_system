"""Customer online payments via the business's own Razorpay keys: checkout, verify,
reconcile (tab closed), owner key settings, and tenant isolation."""

import datetime
import hashlib
import hmac
from decimal import Decimal
from unittest import mock

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.deliveries.models import Delivery
from apps.meals.models import Meal
from apps.notifications.models import Notification
from apps.payments.models import OrderStatus, Payment, PaymentMethod, PaymentOrder
from apps.payments.services import OnlinePaymentService, PaymentService
from apps.plans.models import Plan
from apps.settings_app.models import BusinessSettings
from apps.subscriptions.services import SubscriptionService
from common.constants import Role, SubStatus

KEY_ID = "rzp_test_owner_a"
KEY_SECRET = "owner_a_secret"


def sign(order_id, payment_id, secret=KEY_SECRET):
    return hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()


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
def online_a(biz_a):
    s = BusinessSettings.objects.create(business=biz_a, online_payments_enabled=True, razorpay_key_id=KEY_ID)
    s.set_razorpay_secret(KEY_SECRET)
    s.save()
    return s


@pytest.fixture()
def cust_user_a(biz_a):
    return User.objects.create_user(username="cust_a", password="pass", role=Role.CUSTOMER, business=biz_a)


@pytest.fixture()
def cust_user_b(biz_b):
    return User.objects.create_user(username="cust_b", password="pass", role=Role.CUSTOMER, business=biz_b)


@pytest.fixture()
def cust_a(biz_a, cust_user_a):
    return Customer.objects.create(business=biz_a, user=cust_user_a, name="Alice", phone="9990000001")


@pytest.fixture()
def cust_b(biz_b, cust_user_b):
    return Customer.objects.create(business=biz_b, user=cust_user_b, name="Bob")


@pytest.fixture()
def plan_a(biz_a):
    meal = Meal.objects.create(business=biz_a, name="Lunch")
    return Plan.objects.create(
        business=biz_a, name="Monthly", meal=meal, duration_days=30, total_meals=30, price=Decimal("2500.00")
    )


@pytest.fixture()
def sub_a(biz_a, cust_a, plan_a, owner_a):
    return SubscriptionService.create_subscription(
        business_id=biz_a.id, customer=cust_a, plan=plan_a, start_date=datetime.date.today()
    )


def client_for(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def pay_url(sub):
    return f"/api/v1/portal/subscriptions/{sub.id}/pay/"


@pytest.fixture()
def rz():
    """Mock the Razorpay network calls; signatures are verified for real."""
    with (
        mock.patch("common.razorpay_checkout.create_order") as create_order,
        mock.patch("common.razorpay_checkout.fetch_captured_payment_id", return_value=None) as fetch,
    ):
        create_order.side_effect = lambda *a, **kw: {"id": f"order_{create_order.call_count}"}
        yield mock.Mock(create_order=create_order, fetch=fetch)


@pytest.mark.django_db
class TestCheckoutFlow:
    def test_start_returns_checkout_with_owner_key(self, cust_user_a, sub_a, online_a, rz):
        res = client_for(cust_user_a).post(pay_url(sub_a))
        assert res.status_code == 200
        assert res.data["status"] == "CHECKOUT"
        assert res.data["key_id"] == KEY_ID
        assert res.data["amount"] == 250000  # paise
        assert res.data["name"] == "Mess A"
        assert "secret" not in str(res.data)
        key_id, key_secret = rz.create_order.call_args.args
        assert (key_id, key_secret) == (KEY_ID, KEY_SECRET)
        order = PaymentOrder.objects.get()
        assert order.amount == Decimal("2500.00") and order.status == OrderStatus.CREATED

    def test_verified_payment_activates_subscription(self, cust_user_a, sub_a, online_a, rz):
        c = client_for(cust_user_a)
        order_id = c.post(pay_url(sub_a)).data["order_id"]
        res = c.post(
            pay_url(sub_a) + "verify/",
            {
                "razorpay_order_id": order_id,
                "razorpay_payment_id": "pay_1",
                "razorpay_signature": sign(order_id, "pay_1"),
            },
        )
        assert res.status_code == 200, res.data
        assert res.data["subscription"]["status"] == SubStatus.ACTIVE
        sub_a.refresh_from_db()
        assert sub_a.status == SubStatus.ACTIVE and sub_a.pending_amount == 0
        payment = Payment.objects.get()
        assert payment.method == PaymentMethod.ONLINE and payment.transaction_reference == "pay_1"
        assert Delivery.objects.filter(subscription=sub_a).count() == 30
        assert Notification.objects.filter(title="Payment Received").count() == 1

    def test_bad_signature_records_nothing(self, cust_user_a, sub_a, online_a, rz):
        c = client_for(cust_user_a)
        order_id = c.post(pay_url(sub_a)).data["order_id"]
        res = c.post(
            pay_url(sub_a) + "verify/",
            {"razorpay_order_id": order_id, "razorpay_payment_id": "pay_1", "razorpay_signature": "forged"},
        )
        assert res.status_code == 400
        assert not Payment.objects.exists()
        sub_a.refresh_from_db()
        assert sub_a.status == SubStatus.PENDING

    def test_signed_with_another_secret_is_rejected(self, cust_user_a, sub_a, online_a, rz):
        c = client_for(cust_user_a)
        order_id = c.post(pay_url(sub_a)).data["order_id"]
        res = c.post(
            pay_url(sub_a) + "verify/",
            {
                "razorpay_order_id": order_id,
                "razorpay_payment_id": "pay_1",
                "razorpay_signature": sign(order_id, "pay_1", secret="someone_else"),
            },
        )
        assert res.status_code == 400
        assert not Payment.objects.exists()

    def test_verify_twice_records_once(self, cust_user_a, sub_a, online_a, rz):
        c = client_for(cust_user_a)
        order_id = c.post(pay_url(sub_a)).data["order_id"]
        body = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": "pay_1",
            "razorpay_signature": sign(order_id, "pay_1"),
        }
        assert c.post(pay_url(sub_a) + "verify/", body).status_code == 200
        assert c.post(pay_url(sub_a) + "verify/", body).status_code == 200
        assert Payment.objects.count() == 1

    def test_part_paid_charges_only_the_rest(self, cust_user_a, sub_a, online_a, rz):
        PaymentService.record_payment(
            business_id=sub_a.business_id,
            subscription=sub_a,
            amount=Decimal("1000.00"),
            method=PaymentMethod.CASH,
            payment_date=datetime.date.today(),
        )
        res = client_for(cust_user_a).post(pay_url(sub_a))
        assert res.data["amount"] == 150000

    def test_reopening_reuses_the_open_order(self, cust_user_a, sub_a, online_a, rz):
        c = client_for(cust_user_a)
        first = c.post(pay_url(sub_a)).data["order_id"]
        second = c.post(pay_url(sub_a)).data["order_id"]
        assert first == second
        assert rz.create_order.call_count == 1

    def test_nothing_due_is_rejected(self, cust_user_a, sub_a, online_a, rz):
        sub_a.pending_amount = Decimal("0.00")
        sub_a.save()
        res = client_for(cust_user_a).post(pay_url(sub_a))
        assert res.status_code == 200 and res.data["status"] == "PAID"
        rz.create_order.assert_not_called()

    def test_cancelled_subscription_cannot_be_paid(self, cust_user_a, sub_a, online_a, rz):
        sub_a.status = SubStatus.CANCELLED
        sub_a.save()
        assert client_for(cust_user_a).post(pay_url(sub_a)).status_code == 400

    def test_disabled_when_owner_has_not_set_it_up(self, cust_user_a, sub_a, rz):
        res = client_for(cust_user_a).post(pay_url(sub_a))
        assert res.status_code == 400
        assert "isn't set up" in res.data["error"]["message"]
        assert client_for(cust_user_a).get("/api/v1/portal/online-payment/").data == {"enabled": False}

    def test_enabled_flag(self, cust_user_a, cust_a, online_a):
        assert client_for(cust_user_a).get("/api/v1/portal/online-payment/").data == {"enabled": True}

    def test_razorpay_down_gives_friendly_error(self, cust_user_a, sub_a, online_a):
        with mock.patch("razorpay.Client") as client:
            client.return_value.order.create.side_effect = RuntimeError("boom")
            res = client_for(cust_user_a).post(pay_url(sub_a))
        assert res.status_code == 400
        assert "try again" in res.data["error"]["message"]


@pytest.mark.django_db
class TestReconcile:
    """Customer paid but closed the tab before Checkout confirmed."""

    def test_portal_load_applies_captured_payment(self, cust_user_a, sub_a, online_a, rz):
        c = client_for(cust_user_a)
        c.post(pay_url(sub_a))
        rz.fetch.return_value = "pay_late"
        res = c.get("/api/v1/portal/subscriptions/")
        assert res.data[0]["status"] == SubStatus.ACTIVE
        assert Payment.objects.get().transaction_reference == "pay_late"

    def test_pay_again_finds_earlier_payment_instead_of_charging_twice(
        self, cust_user_a, sub_a, online_a, rz
    ):
        c = client_for(cust_user_a)
        c.post(pay_url(sub_a))
        rz.fetch.return_value = "pay_late"
        res = c.post(pay_url(sub_a))
        assert res.data["status"] == "PAID"
        assert rz.create_order.call_count == 1
        assert Payment.objects.count() == 1

    def test_old_unpaid_orders_expire(self, cust_user_a, sub_a, online_a, rz):
        c = client_for(cust_user_a)
        c.post(pay_url(sub_a))
        PaymentOrder.objects.update(created_at=datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC))
        c.post(pay_url(sub_a))
        assert list(PaymentOrder.objects.order_by("created_at").values_list("status", flat=True)) == [
            OrderStatus.EXPIRED,
            OrderStatus.CREATED,
        ]

    def test_cash_recorded_meanwhile_flags_the_order(self, cust_user_a, sub_a, online_a, rz):
        c = client_for(cust_user_a)
        order_id = c.post(pay_url(sub_a)).data["order_id"]
        PaymentService.record_payment(
            business_id=sub_a.business_id,
            subscription=sub_a,
            amount=Decimal("2500.00"),
            method=PaymentMethod.CASH,
            payment_date=datetime.date.today(),
        )
        res = c.post(
            pay_url(sub_a) + "verify/",
            {
                "razorpay_order_id": order_id,
                "razorpay_payment_id": "pay_dup",
                "razorpay_signature": sign(order_id, "pay_dup"),
            },
        )
        assert res.status_code == 400
        order = PaymentOrder.objects.get()
        assert order.status == OrderStatus.FAILED and "pay_dup" in order.failure_reason
        assert Notification.objects.filter(title="Online payment needs attention").exists()
        assert Payment.objects.count() == 1  # only the cash


@pytest.mark.django_db
class TestIsolation:
    def test_customer_cannot_pay_another_customers_subscription(
        self, cust_user_b, cust_b, sub_a, online_a, rz
    ):
        assert client_for(cust_user_b).post(pay_url(sub_a)).status_code == 404
        rz.create_order.assert_not_called()

    def test_cannot_verify_an_order_of_another_subscription(
        self, biz_a, cust_user_a, cust_a, sub_a, plan_a, online_a, rz
    ):
        other_cust = Customer.objects.create(business=biz_a, name="Other")
        other_sub = SubscriptionService.create_subscription(
            business_id=biz_a.id, customer=other_cust, plan=plan_a, start_date=datetime.date.today()
        )
        order, _ = OnlinePaymentService.start_checkout(other_sub)
        res = client_for(cust_user_a).post(
            pay_url(sub_a) + "verify/",
            {
                "razorpay_order_id": order.razorpay_order_id,
                "razorpay_payment_id": "pay_x",
                "razorpay_signature": sign(order.razorpay_order_id, "pay_x"),
            },
        )
        assert res.status_code == 404
        assert not Payment.objects.exists()

    def test_staff_cannot_use_portal_pay(self, owner_a, sub_a, online_a, rz):
        assert client_for(owner_a).post(pay_url(sub_a)).status_code == 403


@pytest.mark.django_db
class TestOwnerRazorpaySettings:
    URL = "/api/v1/settings/"

    def test_secret_is_encrypted_and_never_returned(self, owner_a, biz_a):
        res = client_for(owner_a).put(
            self.URL,
            {"razorpay_key_id": KEY_ID, "razorpay_key_secret": KEY_SECRET, "online_payments_enabled": True},
            format="json",
        )
        assert res.status_code == 200, res.data
        assert "razorpay_key_secret" not in res.data
        assert res.data["razorpay_configured"] is True and res.data["online_payments_enabled"] is True
        s = BusinessSettings.objects.get(business=biz_a)
        assert KEY_SECRET not in s.razorpay_key_secret_encrypted
        assert s.razorpay_credentials() == (KEY_ID, KEY_SECRET)

    def test_blank_secret_keeps_the_saved_one(self, owner_a, online_a):
        res = client_for(owner_a).put(
            self.URL, {"razorpay_key_secret": "", "max_skip_days": 5}, format="json"
        )
        assert res.status_code == 200
        online_a.refresh_from_db()
        assert online_a.razorpay_credentials() == (KEY_ID, KEY_SECRET)

    def test_clearing_key_id_removes_keys_and_disables(self, owner_a, online_a):
        res = client_for(owner_a).put(self.URL, {"razorpay_key_id": ""}, format="json")
        assert res.status_code == 200
        assert res.data["razorpay_configured"] is False and res.data["online_payments_enabled"] is False

    def test_cannot_enable_without_keys(self, owner_a, biz_a):
        res = client_for(owner_a).put(self.URL, {"online_payments_enabled": True}, format="json")
        assert res.status_code == 400

    def test_key_id_format_checked(self, owner_a, biz_a):
        res = client_for(owner_a).put(self.URL, {"razorpay_key_id": "abc"}, format="json")
        assert res.status_code == 400

    def test_manager_sees_status_but_cannot_change_keys(self, manager_a, online_a):
        c = client_for(manager_a)
        data = c.get(self.URL).data
        assert data["razorpay_configured"] is True and "razorpay_key_secret" not in data
        assert c.put(self.URL, {"razorpay_key_id": ""}, format="json").status_code == 403

    def test_changed_encryption_key_reads_as_not_configured(self, online_a, settings):
        settings.FIELD_ENCRYPTION_KEY = "rotated"
        online_a.refresh_from_db()
        assert online_a.razorpay_credentials() is None and online_a.razorpay_configured is False
