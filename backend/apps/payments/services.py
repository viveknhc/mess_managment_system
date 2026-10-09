"""Payment business logic (PAY-03, PAY-04, PAY-06).

Golden path: record_payment → recalc → if fully paid → ACTIVE.
"""

import datetime
from decimal import Decimal

from django.db import models, transaction

from apps.payments.models import Payment, PaymentStatus
from apps.subscriptions.models import Subscription
from common.constants import Role, SubStatus


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
