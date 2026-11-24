"""Payment business logic (PAY-03, PAY-04, PAY-06).

Golden path: record_payment → recalc → if fully paid → ACTIVE.
"""

import datetime
import logging
import re
from decimal import Decimal
from urllib.parse import urlencode

from django.db import models, transaction
from django.utils import timezone

from apps.customization.registry import ONLINE_PAYMENTS
from apps.customization.services import FeatureService
from apps.payments.models import (
    OrderStatus,
    Payment,
    PaymentMethod,
    PaymentOrder,
    PaymentStatus,
    UpiClaimStatus,
    UpiPaymentClaim,
)
from apps.subscriptions.models import Subscription
from apps.subscriptions.services import SubscriptionService
from common import razorpay_checkout
from common.constants import Role, SubStatus

logger = logging.getLogger(__name__)


class PaymentService:
    @staticmethod
    @transaction.atomic
    def record_payment(
        *, business_id, subscription, amount, method, payment_date, transaction_reference="", notes=""
    ):
        """Record a payment and recalculate subscription amounts.

        If fully paid and subscription is PENDING → transition to ACTIVE,
        then generate delivery schedule and notify owners.
        """
        if amount <= 0:
            raise ValueError("Payment amount must be positive.")

        # Lock first, then check: two payments (or a payment and a cancel) arriving together
        # are serialized here, so the second one sees the first one's result.
        sub = Subscription.objects.select_for_update().select_related("customer").get(id=subscription.id)
        if sub.business_id != business_id:
            raise ValueError("Subscription does not belong to this business.")
        if sub.status in (SubStatus.CANCELLED, SubStatus.EXPIRED):
            raise ValueError(f"Cannot record payment for {sub.status} subscription.")

        # Guard against overpayment
        max_payable = sub.total_amount - sub.paid_amount
        if amount > max_payable:
            raise ValueError(f"Payment of ₹{amount} exceeds pending amount of ₹{max_payable}.")

        payment = Payment.objects.create(
            business_id=business_id,
            subscription=sub,
            customer=sub.customer,
            amount=amount,
            method=method,
            payment_date=payment_date,
            transaction_reference=transaction_reference,
            notes=notes,
            status=PaymentStatus.PAID,
        )

        # Recalculate subscription amounts
        sub.paid_amount += amount
        sub.pending_amount = max(sub.total_amount - sub.paid_amount, Decimal("0.00"))

        # Activation chain: fully paid PENDING → ACTIVE
        was_pending = sub.status == SubStatus.PENDING
        fields = ["paid_amount", "pending_amount", "updated_at"]
        if sub.paid_amount >= sub.total_amount and was_pending:
            fields += SubscriptionService.activate_on_full_payment(sub)

        sub.save(update_fields=fields)

        # Post-activation: generate deliveries + notify owners
        if was_pending and sub.status == SubStatus.ACTIVE:
            from apps.accounts.models import User
            from apps.deliveries.services import DeliveryService
            from apps.notifications.services import NotificationService

            DeliveryService.generate_delivery_schedule(sub)

            owners = User.objects.filter(business_id=business_id, role=Role.OWNER, is_active=True)
            for owner_user in owners:
                NotificationService.emit_subscription_activated(
                    business_id=business_id,
                    user=owner_user,
                    customer_name=sub.customer.name,
                    plan_name=sub.plan.name,
                )

        # Refresh the original object
        subscription.refresh_from_db()
        return payment


OPEN_ORDER_WINDOW = datetime.timedelta(days=2)  # older unpaid orders are given up on
PAYABLE_STATUSES = (SubStatus.PENDING, SubStatus.ACTIVE, SubStatus.PAUSED)


def _business_settings(business_id):
    from apps.settings_app.models import BusinessSettings

    return BusinessSettings.objects.filter(business_id=business_id).first()


class OnlinePaymentService:
    """Customer pays a subscription's pending amount via Razorpay Checkout, into the
    business's own Razorpay account. A verified payment goes through record_payment,
    so activation, deliveries and notifications work exactly as for cash."""

    @staticmethod
    def is_enabled(business_id):
        s = _business_settings(business_id)
        return bool(s and s.razorpay_credentials()) and FeatureService.has(business_id, ONLINE_PAYMENTS)

    @staticmethod
    def start_checkout(subscription):
        """Return (order, key_id) to open Checkout with, or (None, None) if nothing is left to pay
        (e.g. an earlier payment the browser never confirmed was just found and applied)."""
        s = _business_settings(subscription.business_id)
        enabled = s and FeatureService.has(subscription.business_id, ONLINE_PAYMENTS)
        creds = s.razorpay_credentials() if enabled else None
        if not creds:
            raise ValueError("Online payment isn't set up for this mess. Please pay at the mess.")
        if subscription.status not in PAYABLE_STATUSES:
            raise ValueError(f"Cannot pay for a {subscription.status.lower()} subscription.")

        reusable = OnlinePaymentService.reconcile(subscription)
        subscription.refresh_from_db()
        if subscription.pending_amount <= 0:
            return None, None

        key_id, key_secret = creds
        order = next((o for o in reusable if o.amount == subscription.pending_amount), None)
        if order is None:
            rz_order = razorpay_checkout.create_order(
                key_id,
                key_secret,
                amount=subscription.pending_amount,
                receipt=f"sub-{subscription.id.hex[:16]}",
                notes={"subscription_id": str(subscription.id), "customer": subscription.customer.name},
            )
            order = PaymentOrder.objects.create(
                business_id=subscription.business_id,
                subscription=subscription,
                customer=subscription.customer,
                amount=subscription.pending_amount,
                razorpay_order_id=rz_order["id"],
            )
        return order, key_id

    @staticmethod
    def confirm(order, *, payment_id, signature):
        """Checkout success callback. Verifies the signature, then applies the payment."""
        s = _business_settings(order.business_id)
        keys = s.razorpay_keys() if s else None
        if not keys or not razorpay_checkout.verify_payment_signature(
            keys[1], order.razorpay_order_id, payment_id, signature
        ):
            raise ValueError("Payment could not be verified. If money was deducted, contact the mess.")
        order = OnlinePaymentService._complete(order.id, payment_id)
        if order.status == OrderStatus.FAILED:
            raise ValueError(order.failure_reason)
        return order

    @staticmethod
    def reconcile(subscription):
        """Apply payments captured on open orders whose Checkout success never reached us.

        Returns the orders still open (unpaid, recent) so they can be reused.
        """
        s = _business_settings(subscription.business_id)
        keys = s.razorpay_keys() if s else None
        open_orders = list(PaymentOrder.objects.filter(subscription=subscription, status=OrderStatus.CREATED))
        if not keys or not open_orders:
            return []

        still_open = []
        cutoff = timezone.now() - OPEN_ORDER_WINDOW
        for order in open_orders:
            if OnlinePaymentService._apply_if_captured(order, keys):
                continue
            if order.created_at < cutoff:
                PaymentOrder.objects.filter(id=order.id, status=OrderStatus.CREATED).update(
                    status=OrderStatus.EXPIRED
                )
            else:
                still_open.append(order)
        return still_open

    @staticmethod
    def reconcile_customer(customer):
        """Reconcile every subscription of this customer that has a recent open order."""
        subs = Subscription.objects.filter(
            customer=customer,
            payment_orders__status=OrderStatus.CREATED,
            payment_orders__created_at__gte=timezone.now() - OPEN_ORDER_WINDOW,
        ).distinct()
        for sub in subs:
            OnlinePaymentService.reconcile(sub)

    @staticmethod
    def handle_webhook(business_id, order_id):
        """Razorpay says an order of this business was paid. The payload is only a hint:
        the payment is applied only if Razorpay's API, asked with the owner's keys, confirms it.
        Returns True if a payment was applied."""
        order = PaymentOrder.objects.filter(
            business_id=business_id,
            razorpay_order_id=order_id,
            status__in=[OrderStatus.CREATED, OrderStatus.EXPIRED],
        ).first()
        s = _business_settings(business_id)
        keys = s.razorpay_keys() if s else None
        if not order or not keys:
            return False
        return OnlinePaymentService._apply_if_captured(order, keys)

    @staticmethod
    def reconcile_all():
        """Daily safety net: reconcile every recent open order across businesses.
        Catches payments whose Checkout success and webhook both never arrived."""
        subs = Subscription.objects.filter(
            payment_orders__status=OrderStatus.CREATED,
        ).distinct()
        count = 0
        for sub in subs:
            try:
                OnlinePaymentService.reconcile(sub)
                count += 1
            except Exception:
                logger.exception("Online payment reconcile failed for subscription %s", sub.id)
        return count

    @staticmethod
    def _apply_if_captured(order, keys):
        payment_id = razorpay_checkout.fetch_captured_payment_id(*keys, order.razorpay_order_id)
        if not payment_id:
            return False
        OnlinePaymentService._complete(order.id, payment_id)
        return True

    @staticmethod
    def _complete(order_id, payment_id):
        """Record the payment once (idempotent under concurrent confirm/reconcile)."""
        from apps.accounts.models import User
        from apps.notifications.models import NotificationType
        from apps.notifications.services import NotificationService

        with transaction.atomic():
            order = (
                PaymentOrder.objects.select_for_update()
                .select_related("subscription", "customer")
                .get(id=order_id)
            )
            if order.status in (OrderStatus.PAID, OrderStatus.FAILED):
                return order

            order.razorpay_payment_id = payment_id
            try:
                order.payment = PaymentService.record_payment(
                    business_id=order.business_id,
                    subscription=order.subscription,
                    amount=order.amount,
                    method=PaymentMethod.ONLINE,
                    payment_date=datetime.date.today(),
                    transaction_reference=payment_id,
                    notes="Paid online (Razorpay)",
                )
                order.status = OrderStatus.PAID
            except ValueError as e:
                # Money is in the owner's Razorpay account but can't be applied (e.g. cash was
                # recorded meanwhile). Flag it so the owner can refund or adjust.
                order.status = OrderStatus.FAILED
                order.failure_reason = (
                    f"₹{order.amount} was paid online (Razorpay {payment_id}) but could not be applied: {e} "
                    "Please contact the mess."
                )[:255]
                logger.error("Online payment %s for order %s not applied: %s", payment_id, order.id, e)
            order.save()

            owners = User.objects.filter(business_id=order.business_id, role=Role.OWNER, is_active=True)
            s = _business_settings(order.business_id)
            for owner in owners:
                if order.status == OrderStatus.FAILED:
                    NotificationService.emit(
                        business_id=order.business_id,
                        user=owner,
                        notification_type=NotificationType.GENERAL,
                        title="Online payment needs attention",
                        message=f"{order.customer.name}: {order.failure_reason}",
                    )
                elif s is None or s.notify_on_payment:
                    NotificationService.emit_payment_received(
                        business_id=order.business_id,
                        user=owner,
                        amount=order.amount,
                        customer_name=f"{order.customer.name} (online)",
                    )
        return order


UPI_ID_RE = re.compile(r"^[a-zA-Z0-9._-]{2,256}@[a-zA-Z][a-zA-Z0-9.-]{1,63}$")
UTR_RE = re.compile(r"^[a-zA-Z0-9]{6,32}$")


class PaymentMode:
    RAZORPAY = "RAZORPAY"  # automatic: Checkout + verified capture
    UPI = "UPI"  # customer pays the mess's UPI ID; owner confirms


def payment_mode(business_id):
    """How customers of this business pay in the portal. Razorpay wins when both are set up,
    so a customer never sees two competing Pay buttons."""
    if OnlinePaymentService.is_enabled(business_id):
        return PaymentMode.RAZORPAY
    if UpiPaymentService.upi_id(business_id):
        return PaymentMode.UPI
    return None


def _notify_staff(business_id, *, title, message, roles=(Role.OWNER, Role.MANAGER)):
    from apps.accounts.models import User
    from apps.notifications.models import NotificationType
    from apps.notifications.services import NotificationService

    for user in User.objects.filter(business_id=business_id, role__in=roles, is_active=True):
        NotificationService.emit(
            business_id=business_id,
            user=user,
            notification_type=NotificationType.GENERAL,
            title=title,
            message=message,
        )


def _notify_customer(claim, *, notification_type, title, message):
    from apps.notifications.services import NotificationService

    if claim.customer.user_id:
        NotificationService.emit(
            business_id=claim.business_id,
            user=claim.customer.user,
            notification_type=notification_type,
            title=title,
            message=message,
        )


class UpiPaymentService:
    """Customer pays the mess's own UPI ID from any UPI app, taps "I've paid", and the
    owner confirms after seeing the money. No gateway, no fees, nothing to verify
    automatically — so nothing is recorded until a person confirms."""

    @staticmethod
    def upi_id(business_id):
        """The UPI ID customers pay, or "" when UPI payments are off for this business."""
        s = _business_settings(business_id)
        if not (s and s.upi_id) or not FeatureService.has(business_id, ONLINE_PAYMENTS):
            return ""
        return s.upi_id

    @staticmethod
    def payment_link(subscription):
        """upi://pay link with the mess, amount and a note the owner can match in their UPI app.
        Raises ValueError when UPI payment isn't possible for this subscription."""
        vpa = UpiPaymentService.upi_id(subscription.business_id)
        if not vpa:
            raise ValueError("UPI payment isn't set up for this mess. Please pay at the mess.")
        if subscription.status not in PAYABLE_STATUSES:
            raise ValueError(f"Cannot pay for a {subscription.status.lower()} subscription.")
        if subscription.pending_amount <= 0:
            raise ValueError("Nothing is due on this subscription.")
        payee = subscription.business.name[:50]
        note = f"{subscription.customer.name} - {subscription.plan.name}"[:50]
        query = urlencode(
            {"pa": vpa, "pn": payee, "am": f"{subscription.pending_amount:.2f}", "cu": "INR", "tn": note}
        )
        return {
            "upi_url": f"upi://pay?{query}",
            "upi_id": vpa,
            "payee_name": payee,
            "amount": f"{subscription.pending_amount:.2f}",
            "note": note,
        }

    @staticmethod
    def submit_claim(subscription, *, utr=""):
        """Customer says they paid the pending amount. Idempotent: a second tap returns the
        claim already waiting (adding the reference if it was missing)."""
        utr = (utr or "").strip().replace(" ", "")
        if utr and not UTR_RE.match(utr):
            raise ValueError("The UPI reference should be the 12-digit number shown in your UPI app.")
        UpiPaymentService.payment_link(subscription)  # same checks: UPI on, payable, something due

        with transaction.atomic():
            sub = Subscription.objects.select_for_update().select_related("customer").get(id=subscription.id)
            existing = UpiPaymentClaim.objects.filter(subscription=sub, status=UpiClaimStatus.PENDING).first()
            if existing:
                if utr and not existing.utr:
                    existing.utr = utr
                    existing.save(update_fields=["utr", "updated_at"])
                return existing
            claim = UpiPaymentClaim.objects.create(
                business_id=sub.business_id,
                subscription=sub,
                customer=sub.customer,
                amount=sub.pending_amount,
                utr=utr,
            )

        ref = f" (UPI ref {utr})" if utr else ""
        _notify_staff(
            claim.business_id,
            title="UPI payment to confirm",
            message=(
                f"{claim.customer.name} says they paid ₹{claim.amount}{ref}. "
                "Check your UPI app or bank, then confirm it in Customer Payments."
            ),
        )
        return claim

    @staticmethod
    def confirm_claim(claim, *, user):
        """Owner saw the money: record it like any payment (activates a PENDING subscription)."""
        from apps.audit.services import AuditService
        from apps.notifications.models import NotificationType

        with transaction.atomic():
            claim = UpiPaymentClaim.objects.select_for_update().select_related("customer").get(id=claim.id)
            if claim.status != UpiClaimStatus.PENDING:
                raise ValueError(f"This payment was already {claim.get_status_display().lower()}.")
            claim.payment = PaymentService.record_payment(
                business_id=claim.business_id,
                subscription=claim.subscription,
                amount=claim.amount,
                method=PaymentMethod.UPI,
                payment_date=timezone.localdate(claim.created_at),
                transaction_reference=claim.utr,
                notes=f"Paid by UPI, confirmed by {user.name or user.username}",
            )
            claim.status = UpiClaimStatus.CONFIRMED
            claim.reviewed_by = user
            claim.reviewed_at = timezone.now()
            claim.save()
            AuditService.log(
                business_id=claim.business_id,
                user=user,
                action="UPDATE",
                entity_type="UpiPaymentClaim",
                entity_id=claim.id,
                description=f"Confirmed UPI payment of ₹{claim.amount} from {claim.customer.name}",
            )
        _notify_customer(
            claim,
            notification_type=NotificationType.PAYMENT_RECEIVED,
            title="Payment confirmed",
            message=f"The mess confirmed your UPI payment of ₹{claim.amount}. Thank you!",
        )
        return claim

    @staticmethod
    def reject_claim(claim, *, user, reason=""):
        """Owner didn't receive it. Nothing is recorded; the customer can pay again."""
        from apps.audit.services import AuditService
        from apps.notifications.models import NotificationType

        reason = (reason or "").strip()[:200] or "The mess did not receive this payment."
        with transaction.atomic():
            claim = UpiPaymentClaim.objects.select_for_update().select_related("customer").get(id=claim.id)
            if claim.status != UpiClaimStatus.PENDING:
                raise ValueError(f"This payment was already {claim.get_status_display().lower()}.")
            claim.status = UpiClaimStatus.REJECTED
            claim.reject_reason = reason
            claim.reviewed_by = user
            claim.reviewed_at = timezone.now()
            claim.save()
            AuditService.log(
                business_id=claim.business_id,
                user=user,
                action="UPDATE",
                entity_type="UpiPaymentClaim",
                entity_id=claim.id,
                description=f"Rejected UPI payment of ₹{claim.amount} from {claim.customer.name}: {reason}",
            )
        _notify_customer(
            claim,
            notification_type=NotificationType.GENERAL,
            title="UPI payment not received",
            message=f"Your UPI payment of ₹{claim.amount} wasn't confirmed: {reason}",
        )
        return claim


class PaymentSelector:
    @staticmethod
    def get_summary(business_id):
        """Payment summary: today's collection, month total, total pending."""
        today = datetime.date.today()
        month_start = today.replace(day=1)

        paid_qs = Payment.objects.filter(business_id=business_id, status=PaymentStatus.PAID)

        today_total = paid_qs.filter(payment_date=today).aggregate(total=models.Sum("amount"))[
            "total"
        ] or Decimal("0.00")

        month_total = paid_qs.filter(payment_date__gte=month_start).aggregate(total=models.Sum("amount"))[
            "total"
        ] or Decimal("0.00")

        total_pending = Subscription.objects.filter(
            business_id=business_id,
            status__in=[SubStatus.PENDING, SubStatus.ACTIVE, SubStatus.PAUSED],
        ).aggregate(total=models.Sum("pending_amount"))["total"] or Decimal("0.00")

        return {
            "today": today_total,
            "month": month_total,
            "pending": total_pending,
        }
