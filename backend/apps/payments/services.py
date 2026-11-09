"""Payment business logic (PAY-03, PAY-04, PAY-06).

Golden path: record_payment → recalc → if fully paid → ACTIVE.
"""

import datetime
import logging
from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone

from apps.payments.models import OrderStatus, Payment, PaymentMethod, PaymentOrder, PaymentStatus
from apps.subscriptions.models import Subscription
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
        if subscription.business_id != business_id:
            raise ValueError("Subscription does not belong to this business.")
        if amount <= 0:
            raise ValueError("Payment amount must be positive.")
        if subscription.status in (SubStatus.CANCELLED, SubStatus.EXPIRED):
            raise ValueError(f"Cannot record payment for {subscription.status} subscription.")

        # Guard against overpayment
        max_payable = subscription.total_amount - subscription.paid_amount
        if amount > max_payable:
            raise ValueError(f"Payment of ₹{amount} exceeds pending amount of ₹{max_payable}.")

        payment = Payment.objects.create(
            business_id=business_id,
            subscription=subscription,
            customer=subscription.customer,
            amount=amount,
            method=method,
            payment_date=payment_date,
            transaction_reference=transaction_reference,
            notes=notes,
            status=PaymentStatus.PAID,
        )

        # Recalculate subscription amounts
        sub = Subscription.objects.select_for_update().get(id=subscription.id)
        sub.paid_amount += amount
        sub.pending_amount = max(sub.total_amount - sub.paid_amount, Decimal("0.00"))

        # Activation chain: fully paid PENDING → ACTIVE
        was_pending = sub.status == SubStatus.PENDING
        if sub.paid_amount >= sub.total_amount and was_pending:
            sub.status = SubStatus.ACTIVE

        sub.save(update_fields=["paid_amount", "pending_amount", "status", "updated_at"])

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
        return bool(s and s.razorpay_credentials())

    @staticmethod
    def start_checkout(subscription):
        """Return (order, key_id) to open Checkout with, or (None, None) if nothing is left to pay
        (e.g. an earlier payment the browser never confirmed was just found and applied)."""
        s = _business_settings(subscription.business_id)
        creds = s.razorpay_credentials() if s else None
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
            payment_id = razorpay_checkout.fetch_captured_payment_id(*keys, order.razorpay_order_id)
            if payment_id:
                OnlinePaymentService._complete(order.id, payment_id)
            elif order.created_at < cutoff:
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
