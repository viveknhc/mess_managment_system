"""Owner pays the MessDeck fee online (Razorpay Checkout with platform keys):
checkout, verify, webhook/reconcile for closed tabs, suspended businesses, isolation."""

import hashlib
import hmac
import json
from decimal import Decimal
from unittest import mock

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.platform.models import CheckoutStatus, PaymentMethod, SaasCheckoutOrder, SaasPayment, SaasStatus
from apps.platform.services import PlatformService
from common.constants import Role, Status

KEY_ID = "rzp_test_platform"
KEY_SECRET = "platform_secret"
WEBHOOK_SECRET = "whsec_test"
FIRST_PAYMENT = Decimal("3000.00")  # setup 2500 + first month 500

PAY = "/api/v1/billing/pay/"
VERIFY = "/api/v1/billing/pay/verify/"


def sign(order_id, payment_id, secret=KEY_SECRET):
    return hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def platform_keys(settings):
    settings.RAZORPAY_KEY_ID = KEY_ID
    settings.RAZORPAY_KEY_SECRET = KEY_SECRET
    settings.RAZORPAY_WEBHOOK_SECRET = WEBHOOK_SECRET


@pytest.fixture()
def rz():
    with (
        mock.patch("common.razorpay_checkout.create_order") as create_order,
        mock.patch("common.razorpay_checkout.fetch_captured_payment_id", return_value=None) as fetch,
    ):
        create_order.side_effect = lambda *a, **kw: {"id": f"order_{create_order.call_count}"}
        yield mock.Mock(create_order=create_order, fetch=fetch)


@pytest.fixture()
def biz_a(db):
    return Business.objects.create(name="Mess A")


@pytest.fixture()
def owner_a(biz_a):
    return User.objects.create_user(
        username="owner_a", password="pass", role=Role.OWNER, business=biz_a, email="a@example.com"
    )


@pytest.fixture()
def sub_a(biz_a):
    return PlatformService.start_billing(biz_a)


@pytest.fixture()
def client_a(owner_a):
    c = APIClient()
    c.force_authenticate(user=owner_a)
    return c


def verify_body(order_id, payment_id="pay_1", secret=KEY_SECRET):
    return {
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": sign(order_id, payment_id, secret),
    }


@pytest.mark.django_db
class TestBillingCheckout:
    def test_billing_says_online_payment_is_available(self, client_a, sub_a):
        assert client_a.get("/api/v1/billing/").data["online_payment_enabled"] is True

    def test_not_available_without_platform_keys(self, client_a, sub_a, settings, rz):
        settings.RAZORPAY_KEY_SECRET = ""
        assert client_a.get("/api/v1/billing/").data["online_payment_enabled"] is False
        assert client_a.post(PAY).status_code == 400
        rz.create_order.assert_not_called()

    def test_start_charges_exactly_what_is_due(self, client_a, sub_a, rz):
        res = client_a.post(PAY)
        assert res.status_code == 200
        assert res.data["status"] == "CHECKOUT" and res.data["key_id"] == KEY_ID
        assert res.data["amount"] == 300000
        assert res.data["prefill"]["email"] == "a@example.com"
        assert rz.create_order.call_args.args == (KEY_ID, KEY_SECRET)
        assert rz.create_order.call_args.kwargs["amount"] == FIRST_PAYMENT

    def test_verified_payment_activates_billing(self, client_a, sub_a, rz):
        order_id = client_a.post(PAY).data["order_id"]
        res = client_a.post(VERIFY, verify_body(order_id))
        assert res.status_code == 200, res.data
        assert res.data["subscription"]["status"] == SaasStatus.ACTIVE
        payment = SaasPayment.objects.get()
        assert payment.method == PaymentMethod.RAZORPAY
        assert (payment.razorpay_payment_id, payment.razorpay_order_id) == ("pay_1", order_id)
        assert payment.amount == FIRST_PAYMENT and payment.setup_fee == Decimal("2500.00")
        assert SaasCheckoutOrder.objects.get().status == CheckoutStatus.PAID

    def test_bad_signature_records_nothing(self, client_a, sub_a, rz):
        order_id = client_a.post(PAY).data["order_id"]
        res = client_a.post(VERIFY, verify_body(order_id, secret="forged"))
        assert res.status_code == 400
        assert not SaasPayment.objects.exists()

    def test_verify_twice_records_once(self, client_a, sub_a, rz):
        order_id = client_a.post(PAY).data["order_id"]
        client_a.post(VERIFY, verify_body(order_id))
        assert client_a.post(VERIFY, verify_body(order_id)).status_code == 200
        assert SaasPayment.objects.count() == 1

    def test_reopening_reuses_open_order(self, client_a, sub_a, rz):
        assert client_a.post(PAY).data["order_id"] == client_a.post(PAY).data["order_id"]
        assert rz.create_order.call_count == 1

    def test_suspended_business_can_pay_to_restore_access(self, owner_a, biz_a, sub_a, rz):
        PlatformService.suspend_business(biz_a)
        c = APIClient()  # real JWT login: suspension is enforced in authentication
        login = c.post("/api/v1/auth/login/", {"username": "owner_a", "password": "pass"})
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")
        assert c.get("/api/v1/customers/").status_code == 403

        order_id = c.post(PAY).data["order_id"]
        assert c.post(VERIFY, verify_body(order_id)).status_code == 200
        biz_a.refresh_from_db()
        assert biz_a.status == Status.ACTIVE
        assert c.get("/api/v1/customers/").status_code == 200

    def test_staff_cannot_pay(self, biz_a, sub_a, rz):
        staff = User.objects.create_user(
            username="staff", password="pass", role=Role.DELIVERY_STAFF, business=biz_a
        )
        c = APIClient()
        c.force_authenticate(user=staff)
        assert c.post(PAY).status_code == 403

    def test_cannot_verify_another_business_order(self, client_a, sub_a, rz):
        biz_b = Business.objects.create(name="Mess B")
        order_b, _ = PlatformService.start_checkout(PlatformService.start_billing(biz_b))
        res = client_a.post(VERIFY, verify_body(order_b.razorpay_order_id))
        assert res.status_code == 404
        assert not SaasPayment.objects.exists()


@pytest.mark.django_db
class TestClosedTab:
    """Owner paid but the browser never confirmed."""

    def test_pay_again_applies_earlier_payment(self, client_a, sub_a, rz):
        client_a.post(PAY)
        rz.fetch.return_value = "pay_late"
        res = client_a.post(PAY)
        assert res.data["status"] == "PAID"
        assert SaasPayment.objects.get().razorpay_payment_id == "pay_late"
        assert rz.create_order.call_count == 1

    def _webhook(self, payload, secret=WEBHOOK_SECRET):
        body = json.dumps(payload).encode()
        return APIClient().post(
            "/api/v1/webhooks/razorpay/",
            body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=hmac.new(secret.encode(), body, hashlib.sha256).hexdigest(),
        )

    def _order_paid(self, order_id, status="captured"):
        return {
            "event": "order.paid",
            "payload": {
                "order": {"entity": {"id": order_id}},
                "payment": {"entity": {"id": "pay_hook", "order_id": order_id, "status": status}},
            },
        }

    def test_order_paid_webhook_records_payment(self, client_a, sub_a, rz):
        order_id = client_a.post(PAY).data["order_id"]
        assert self._webhook(self._order_paid(order_id)).status_code == 200
        sub_a.refresh_from_db()
        assert sub_a.status == SaasStatus.ACTIVE
        assert SaasPayment.objects.get().razorpay_payment_id == "pay_hook"

    def test_webhook_then_checkout_confirm_records_once(self, client_a, sub_a, rz):
        order_id = client_a.post(PAY).data["order_id"]
        self._webhook(self._order_paid(order_id))
        assert client_a.post(VERIFY, verify_body(order_id, "pay_hook")).status_code == 200
        assert SaasPayment.objects.count() == 1

    def test_webhook_ignores_unknown_and_uncaptured_orders(self, client_a, sub_a, rz):
        order_id = client_a.post(PAY).data["order_id"]
        assert self._webhook(self._order_paid("order_customer_side")).json() == {"status": "ignored"}
        assert self._webhook(self._order_paid(order_id, status="authorized")).json() == {"status": "ignored"}
        assert not SaasPayment.objects.exists()

    def test_webhook_signature_still_required(self, client_a, sub_a, rz):
        order_id = client_a.post(PAY).data["order_id"]
        assert self._webhook(self._order_paid(order_id), secret="wrong").status_code == 400
        assert not SaasPayment.objects.exists()

    def test_amount_changed_meanwhile_is_flagged_not_applied(self, client_a, sub_a, rz):
        order_id = client_a.post(PAY).data["order_id"]
        PlatformService.record_manual_payment(sub_a, amount=FIRST_PAYMENT, method="UPI")  # paid by UPI too
        res = client_a.post(VERIFY, verify_body(order_id, "pay_dup"))
        assert res.status_code == 400
        order = SaasCheckoutOrder.objects.get()
        assert order.status == CheckoutStatus.FAILED and "pay_dup" in order.failure_reason
        assert SaasPayment.objects.count() == 1
