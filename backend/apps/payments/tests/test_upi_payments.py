"""UPI payments straight to the mess's UPI ID: settings, portal pay link, "I've paid"
claims, owner confirm/reject (payment math + activation), Razorpay priority, isolation."""

import datetime
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import pytest

from apps.customers.models import Customer
from apps.customization.registry import ONLINE_PAYMENTS
from apps.customization.services import FeatureService
from apps.deliveries.models import Delivery
from apps.notifications.models import Notification
from apps.payments.models import Payment, PaymentMethod, UpiClaimStatus, UpiPaymentClaim
from apps.payments.services import PaymentService, UpiPaymentService
from apps.payments.tests.test_online_payments import client_for, pay_url
from apps.settings_app.models import BusinessSettings
from apps.subscriptions.services import SubscriptionService
from common.constants import Role, SubStatus

UPI_ID = "annapurna@okicici"
SETTINGS_URL = "/api/v1/settings/"


@pytest.fixture()
def upi_a(biz_a):
    s, _ = BusinessSettings.objects.get_or_create(business=biz_a)
    s.upi_id = UPI_ID
    s.save()
    return s


def claim_url(sub):
    return pay_url(sub) + "upi-claim/"


def info(user):
    return client_for(user).get("/api/v1/portal/online-payment/").data


def owner_claims_url(claim=None, action=""):
    base = "/api/v1/upi-claims/"
    return f"{base}{claim.id}/{action}/" if claim else base


@pytest.mark.django_db
class TestUpiSettings:
    def test_owner_sets_upi_id_normalized(self, owner_a, biz_a):
        res = client_for(owner_a).put(SETTINGS_URL, {"upi_id": "  Annapurna@OKICICI "}, format="json")
        assert res.status_code == 200, res.data
        assert res.data["upi_id"] == UPI_ID
        assert BusinessSettings.objects.get(business=biz_a).upi_id == UPI_ID

    @pytest.mark.parametrize("bad", ["annapurna", "@okicici", "a@1bank", "name@ok icici", "x@y"])
    def test_invalid_upi_id_rejected(self, owner_a, biz_a, bad):
        res = client_for(owner_a).put(SETTINGS_URL, {"upi_id": bad}, format="json")
        assert res.status_code == 400

    def test_blank_clears_upi(self, owner_a, upi_a, cust_user_a, cust_a):
        assert client_for(owner_a).put(SETTINGS_URL, {"upi_id": ""}, format="json").status_code == 200
        assert info(cust_user_a)["mode"] is None

    def test_manager_cannot_change_upi_id(self, manager_a, biz_a):
        res = client_for(manager_a).put(SETTINGS_URL, {"upi_id": UPI_ID}, format="json")
        assert res.status_code == 403

    def test_cannot_set_when_feature_off(self, owner_a, biz_a):
        BusinessSettings.objects.get_or_create(business=biz_a)
        FeatureService.set_overrides(biz_a.id, {ONLINE_PAYMENTS: False})
        res = client_for(owner_a).put(SETTINGS_URL, {"upi_id": UPI_ID}, format="json")
        assert res.status_code == 400


@pytest.mark.django_db
class TestPaymentMode:
    def test_no_setup_means_no_online_payment(self, cust_user_a, cust_a, biz_a):
        data = info(cust_user_a)
        assert data["enabled"] is False and data["mode"] is None

    def test_upi_only(self, cust_user_a, cust_a, upi_a):
        data = info(cust_user_a)
        assert data["enabled"] is True and data["mode"] == "UPI"

    def test_razorpay_wins_when_both_set_up(self, cust_user_a, sub_a, online_a, upi_a, rz):
        assert info(cust_user_a)["mode"] == "RAZORPAY"
        assert client_for(cust_user_a).post(pay_url(sub_a)).data["status"] == "CHECKOUT"

    def test_feature_off_hides_upi(self, cust_user_a, cust_a, upi_a, biz_a):
        FeatureService.set_overrides(biz_a.id, {ONLINE_PAYMENTS: False})
        assert info(cust_user_a)["mode"] is None


@pytest.mark.django_db
class TestUpiPayLink:
    def test_pay_returns_upi_link_for_pending_amount(self, cust_user_a, sub_a, upi_a):
        res = client_for(cust_user_a).post(pay_url(sub_a))
        assert res.status_code == 200, res.data
        assert res.data["status"] == "UPI"
        assert res.data["upi_id"] == UPI_ID and res.data["amount"] == "2500.00"
        url = urlparse(res.data["upi_url"])
        assert url.scheme == "upi" and url.netloc == "pay"
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        assert q == {
            "pa": UPI_ID,
            "pn": "Mess A",
            "am": "2500.00",
            "cu": "INR",
            "tn": "Alice - Monthly",
        }

    def test_link_uses_remaining_amount_after_part_payment(self, cust_user_a, sub_a, upi_a, biz_a):
        PaymentService.record_payment(
            business_id=biz_a.id,
            subscription=sub_a,
            amount=Decimal("1000.00"),
            method=PaymentMethod.CASH,
            payment_date=datetime.date.today(),
        )
        assert client_for(cust_user_a).post(pay_url(sub_a)).data["amount"] == "1500.00"

    def test_nothing_due_returns_paid(self, cust_user_a, sub_a, upi_a, biz_a):
        PaymentService.record_payment(
            business_id=biz_a.id,
            subscription=sub_a,
            amount=Decimal("2500.00"),
            method=PaymentMethod.CASH,
            payment_date=datetime.date.today(),
        )
        assert client_for(cust_user_a).post(pay_url(sub_a)).data["status"] == "PAID"

    def test_cancelled_subscription_cannot_be_paid(self, cust_user_a, sub_a, upi_a):
        sub_a.status = SubStatus.CANCELLED
        sub_a.save(update_fields=["status"])
        assert client_for(cust_user_a).post(pay_url(sub_a)).status_code == 400


@pytest.mark.django_db
class TestUpiClaim:
    def test_claim_waits_for_owner_and_records_nothing(self, cust_user_a, sub_a, upi_a, owner_a, manager_a):
        res = client_for(cust_user_a).post(claim_url(sub_a), {"utr": "4123 4567 8901"}, format="json")
        assert res.status_code == 201, res.data
        assert res.data["status"] == "PENDING" and res.data["amount"] == "2500.00"
        claim = UpiPaymentClaim.objects.get()
        assert claim.utr == "412345678901" and claim.customer_id == sub_a.customer_id
        sub_a.refresh_from_db()
        assert sub_a.status == SubStatus.PENDING and sub_a.paid_amount == 0
        assert not Payment.objects.exists()
        # owner and manager are told to check
        notified = set(
            Notification.objects.filter(title="UPI payment to confirm").values_list("user", flat=True)
        )
        assert notified == {owner_a.id, manager_a.id}

    def test_second_tap_returns_same_claim_and_adds_reference(self, cust_user_a, sub_a, upi_a, owner_a):
        c = client_for(cust_user_a)
        first = c.post(claim_url(sub_a), {}, format="json").data
        second = c.post(claim_url(sub_a), {"utr": "412345678901"}, format="json").data
        assert first["id"] == second["id"]
        assert UpiPaymentClaim.objects.get().utr == "412345678901"

    def test_bad_reference_rejected(self, cust_user_a, sub_a, upi_a):
        res = client_for(cust_user_a).post(claim_url(sub_a), {"utr": "12-ab"}, format="json")
        assert res.status_code == 400
        assert not UpiPaymentClaim.objects.exists()

    def test_cannot_claim_when_upi_off(self, cust_user_a, sub_a):
        assert client_for(cust_user_a).post(claim_url(sub_a), {}, format="json").status_code == 400

    def test_portal_lists_pending_claim(self, cust_user_a, sub_a, upi_a, owner_a):
        client_for(cust_user_a).post(claim_url(sub_a), {}, format="json")
        claims = info(cust_user_a)["upi_claims"]
        assert len(claims) == 1
        assert claims[0]["subscription"] == str(sub_a.id) and claims[0]["status"] == "PENDING"


@pytest.mark.django_db
class TestOwnerReview:
    @pytest.fixture()
    def claim(self, sub_a, upi_a, owner_a):
        return UpiPaymentService.submit_claim(sub_a, utr="412345678901")

    def test_owner_lists_pending_claims(self, owner_a, claim):
        res = client_for(owner_a).get(owner_claims_url() + "?status=PENDING")
        assert res.status_code == 200
        row = res.data["results"][0]
        assert row["customer_name"] == "Alice" and row["amount"] == "2500.00" and row["utr"] == "412345678901"

    def test_confirm_records_upi_payment_and_activates(self, owner_a, claim, sub_a, cust_user_a):
        res = client_for(owner_a).post(owner_claims_url(claim, "confirm"))
        assert res.status_code == 200, res.data
        assert res.data["status"] == "CONFIRMED" and res.data["reviewed_by_name"]
        payment = Payment.objects.get()
        assert payment.amount == Decimal("2500.00") and payment.method == PaymentMethod.UPI
        assert payment.transaction_reference == "412345678901"
        sub_a.refresh_from_db()
        assert sub_a.status == SubStatus.ACTIVE
        assert sub_a.paid_amount == Decimal("2500.00") and sub_a.pending_amount == Decimal("0.00")
        assert Delivery.objects.filter(subscription=sub_a).exists()
        assert Notification.objects.filter(user=cust_user_a, title="Payment confirmed").exists()

    def test_confirm_twice_is_refused(self, owner_a, claim):
        c = client_for(owner_a)
        assert c.post(owner_claims_url(claim, "confirm")).status_code == 200
        assert c.post(owner_claims_url(claim, "confirm")).status_code == 400
        assert Payment.objects.count() == 1

    def test_confirm_refused_if_cash_already_covered_it(self, owner_a, claim, sub_a, biz_a):
        PaymentService.record_payment(
            business_id=biz_a.id,
            subscription=sub_a,
            amount=Decimal("2500.00"),
            method=PaymentMethod.CASH,
            payment_date=datetime.date.today(),
        )
        res = client_for(owner_a).post(owner_claims_url(claim, "confirm"))
        assert res.status_code == 400
        assert Payment.objects.count() == 1
        claim.refresh_from_db()
        assert claim.status == UpiClaimStatus.PENDING  # owner can reject it instead

    def test_reject_records_nothing_and_tells_customer(self, owner_a, claim, sub_a, cust_user_a):
        res = client_for(owner_a).post(owner_claims_url(claim, "reject"), {"reason": "Not in my bank"})
        assert res.status_code == 200
        assert res.data["status"] == "REJECTED" and res.data["reject_reason"] == "Not in my bank"
        assert not Payment.objects.exists()
        sub_a.refresh_from_db()
        assert sub_a.status == SubStatus.PENDING
        assert Notification.objects.filter(user=cust_user_a, title="UPI payment not received").exists()
        # shown to the customer, who can claim again
        assert info(cust_user_a)["upi_claims"][0]["status"] == "REJECTED"
        c = client_for(cust_user_a)
        assert c.post(claim_url(sub_a), {}, format="json").status_code == 201
        assert UpiPaymentClaim.objects.filter(status=UpiClaimStatus.PENDING).count() == 1

    def test_manager_can_review(self, manager_a, claim):
        assert client_for(manager_a).post(owner_claims_url(claim, "confirm")).status_code == 200

    @pytest.mark.parametrize("role", [Role.DELIVERY_STAFF, Role.KITCHEN_STAFF, Role.CUSTOMER])
    def test_other_roles_cannot_review(self, biz_a, claim, role):
        from apps.accounts.models import User

        u = User.objects.create_user(username=f"u_{role}", password="pass", role=role, business=biz_a)
        c = client_for(u)
        assert c.get(owner_claims_url()).status_code == 403
        assert c.post(owner_claims_url(claim, "confirm")).status_code == 403
        assert not Payment.objects.exists()

    def test_claims_cannot_be_created_through_owner_api(self, owner_a, claim, sub_a):
        res = client_for(owner_a).post(owner_claims_url(), {"subscription": str(sub_a.id), "amount": "1"})
        assert res.status_code in (403, 404, 405)
        assert UpiPaymentClaim.objects.count() == 1


@pytest.mark.django_db
class TestUpiIsolation:
    def test_owner_of_other_business_gets_404(self, biz_b, sub_a, upi_a, owner_a):
        from apps.accounts.models import User

        claim = UpiPaymentService.submit_claim(sub_a)
        owner_b = User.objects.create_user(
            username="owner_b", password="pass", role=Role.OWNER, business=biz_b
        )
        c = client_for(owner_b)
        assert c.get(owner_claims_url()).data["count"] == 0
        assert c.post(owner_claims_url(claim, "confirm")).status_code == 404
        assert c.post(owner_claims_url(claim, "reject")).status_code == 404
        claim.refresh_from_db()
        assert claim.status == UpiClaimStatus.PENDING

    def test_customer_cannot_claim_for_another_customers_subscription(
        self, cust_user_b, cust_b, sub_a, upi_a
    ):
        assert client_for(cust_user_b).post(claim_url(sub_a), {}, format="json").status_code == 404
        assert not UpiPaymentClaim.objects.exists()

    def test_customer_only_sees_own_claims(self, biz_a, cust_user_a, sub_a, plan_a, upi_a, owner_a):
        other = Customer.objects.create(business=biz_a, name="Other")
        other_sub = SubscriptionService.create_subscription(
            business_id=biz_a.id, customer=other, plan=plan_a, start_date=datetime.date.today()
        )
        UpiPaymentService.submit_claim(other_sub)
        assert info(cust_user_a)["upi_claims"] == []
