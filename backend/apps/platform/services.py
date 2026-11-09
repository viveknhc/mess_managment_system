"""Platform billing business logic — thin views call these methods."""

import calendar
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.businesses.models import Business
from apps.platform.models import (
    CheckoutStatus,
    PaymentMethod,
    PaymentStatus,
    SaasCheckoutOrder,
    SaasPayment,
    SaasPlan,
    SaasStatus,
    SaasSubscription,
)
from common import razorpay_checkout
from common.constants import Status

logger = logging.getLogger(__name__)

MAX_PAYMENT_FAILURES = 3

# Terms from docs/Monthly_Subscription_Plan.pdf
MONTHLY_PLAN_NAME = "Monthly Plan"
MONTHLY_PLAN_DEFAULTS = {
    "price_monthly": Decimal("500.00"),
    "setup_fee": Decimal("2500.00"),
    "reactivation_fee": Decimal("1000.00"),
    "max_customers": 0,
    "max_staff": 0,
    "features": [
        "Customer management with full records",
        "Meal and plan setup (breakfast, lunch, dinner, tiffin)",
        "Subscription tracking with automatic expiry alerts",
        "Payment recording with paid and pending balances",
        "Daily delivery list and meal counts",
        "Skip and pause handling",
        "Dashboard with today's summary",
        "Owner login plus staff logins",
        "Daily data backup",
        "WhatsApp and email support",
    ],
}
GRACE_DAYS = 7  # unpaid this many days after the due date → suspended
REACTIVATION_GAP_MONTHS = 3  # returning after MORE than this → reactivation fee
DEFAULT_MEALS = ["Breakfast", "Lunch", "Dinner", "Tiffin"]
CHECKOUT_OPEN_WINDOW = timedelta(days=2)  # older unpaid Checkout orders are given up on


def add_months(d: date, months: int) -> date:
    """Same day N months later, clamped to month end (31 Jan + 1 → 28/29 Feb)."""
    month_index = d.month - 1 + months
    year, month = d.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


@dataclass(frozen=True)
class AmountDue:
    setup_fee: Decimal
    reactivation_fee: Decimal
    monthly_fee: Decimal
    due_date: date

    @property
    def total(self) -> Decimal:
        return self.setup_fee + self.reactivation_fee + self.monthly_fee


class PlatformService:
    @staticmethod
    def get_monthly_plan():
        """The standard plan from the PDF — created with the PDF's prices if missing."""
        plan, _ = SaasPlan.objects.get_or_create(name=MONTHLY_PLAN_NAME, defaults=MONTHLY_PLAN_DEFAULTS)
        return plan

    @staticmethod
    @transaction.atomic
    def start_billing(business, plan=None):
        """Create the SaasSubscription in PENDING — first payment (setup + first month) is due."""
        sub, created = SaasSubscription.objects.get_or_create(
            business=business,
            defaults={"status": SaasStatus.PENDING, "plan": plan or PlatformService.get_monthly_plan()},
        )
        if not created:
            logger.info("SaasSubscription already exists for business %s", business.id)
        return sub

    @staticmethod
    @transaction.atomic
    def create_business(
        *,
        name,
        owner_username,
        owner_password,
        owner_name="",
        owner_email="",
        owner_phone="",
        phone="",
        email="",
        address="",
    ):
        """SUPER_ADMIN onboarding: Business + Owner + default meals + billing (first payment due)."""
        from apps.accounts.models import User
        from apps.meals.models import Meal
        from common.constants import Role

        business = Business.objects.create(
            name=name, phone=phone, email=email, address=address, status=Status.ACTIVE
        )
        user = User.objects.create_user(
            username=owner_username,
            password=owner_password,
            name=owner_name,
            email=owner_email,
            phone=owner_phone,
            role=Role.OWNER,
            business=business,
            is_active=True,
        )
        for meal_name in DEFAULT_MEALS:
            Meal.objects.create(business=business, name=meal_name)
        PlatformService.start_billing(business)
        return business, user

    @staticmethod
    def amount_due(subscription, today=None):
        """What the business must pay next, per the PDF terms.

        - First payment: setup fee + first month.
        - After that: the monthly fee, due on current_period_end.
        - Coming back more than 3 months after the paid period ended: + reactivation fee.
        """
        today = today or timezone.now().date()
        plan = subscription.plan or PlatformService.get_monthly_plan()
        zero = Decimal("0.00")
        end = subscription.current_period_end

        if not subscription.setup_fee_paid:
            return AmountDue(plan.setup_fee, zero, plan.price_monthly, today)

        lapsed = end is not None and today > add_months(end, REACTIVATION_GAP_MONTHS)
        return AmountDue(
            setup_fee=zero,
            reactivation_fee=plan.reactivation_fee if lapsed else zero,
            monthly_fee=plan.price_monthly,
            due_date=today if lapsed or end is None else end,
        )

    @staticmethod
    @transaction.atomic
    def record_manual_payment(
        subscription,
        *,
        amount,
        method,
        reference="",
        recorded_by=None,
        today=None,
        razorpay_payment_id="",
        razorpay_order_id="",
    ):
        """SUPER_ADMIN records a UPI/cash/bank payment. Amount must equal what is due.

        Pays for one month. The month continues from the previous due date if the business
        is still within the grace period; otherwise it starts today.
        """
        today = today or timezone.now().date()
        subscription = (
            SaasSubscription.objects.select_for_update().select_related("business").get(pk=subscription.pk)
        )
        due = PlatformService.amount_due(subscription, today)
        amount = Decimal(str(amount))
        if amount != due.total:
            raise ValueError(f"Amount due is ₹{due.total}. Record exactly that amount.")

        end = subscription.current_period_end
        continuing = (
            subscription.setup_fee_paid and end is not None and today < end + timedelta(days=GRACE_DAYS)
        )
        period_start = end if continuing else today
        period_end = add_months(period_start, 1)

        payment = SaasPayment.objects.create(
            saas_subscription=subscription,
            business=subscription.business,
            plan=subscription.plan,
            amount=amount,
            setup_fee=due.setup_fee,
            reactivation_fee=due.reactivation_fee,
            status=PaymentStatus.PAID,
            method=method,
            reference=reference,
            recorded_by=recorded_by,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_order_id=razorpay_order_id,
            period_start=period_start,
            period_end=period_end,
        )
        subscription.plan = subscription.plan or PlatformService.get_monthly_plan()
        subscription.status = SaasStatus.ACTIVE
        subscription.setup_fee_paid = True
        subscription.cancelled_at = None
        subscription.payment_failure_count = 0
        subscription.current_period_start = period_start
        subscription.current_period_end = period_end
        subscription.save()

        business = subscription.business
        if business.status == Status.SUSPENDED:
            business.status = Status.ACTIVE
            business.save(update_fields=["status"])
        return payment

    # ── Owner pays online (Razorpay Checkout, platform keys) ──────────────

    @staticmethod
    def online_payment_enabled():
        return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)

    @staticmethod
    def start_checkout(subscription):
        """Return (order, key_id) for Checkout, or (None, None) if an unconfirmed payment
        was just found and applied, so nothing is due now."""
        if not PlatformService.online_payment_enabled():
            raise ValueError(
                "Online payment isn't available yet. Please pay by UPI and send us the reference."
            )
        if PlatformService.reconcile_checkout(subscription):
            return None, None

        due = PlatformService.amount_due(subscription).total
        reusable = SaasCheckoutOrder.objects.filter(
            saas_subscription=subscription,
            status=CheckoutStatus.CREATED,
            amount=due,
            created_at__gte=timezone.now() - CHECKOUT_OPEN_WINDOW,
        ).first()
        if reusable:
            return reusable, settings.RAZORPAY_KEY_ID

        rz_order = razorpay_checkout.create_order(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET,
            amount=due,
            receipt=f"saas-{subscription.id.hex[:16]}",
            notes={"business_id": str(subscription.business_id), "business": subscription.business.name},
        )
        order = SaasCheckoutOrder.objects.create(
            saas_subscription=subscription, amount=due, razorpay_order_id=rz_order["id"]
        )
        return order, settings.RAZORPAY_KEY_ID

    @staticmethod
    def confirm_checkout(order, *, payment_id, signature):
        """Checkout success callback: verify the signature, then record the payment."""
        if not razorpay_checkout.verify_payment_signature(
            settings.RAZORPAY_KEY_SECRET, order.razorpay_order_id, payment_id, signature
        ):
            raise ValueError("Payment could not be verified. If money was deducted, contact support.")
        order = PlatformService.complete_checkout(order.razorpay_order_id, payment_id)
        if order.status == CheckoutStatus.FAILED:
            raise ValueError(order.failure_reason)
        return order

    @staticmethod
    def reconcile_checkout(subscription):
        """Apply captured payments on open orders whose success never reached us. True if any applied."""
        applied = False
        cutoff = timezone.now() - CHECKOUT_OPEN_WINDOW
        open_orders = SaasCheckoutOrder.objects.filter(
            saas_subscription=subscription, status=CheckoutStatus.CREATED
        )
        for order in open_orders:
            payment_id = razorpay_checkout.fetch_captured_payment_id(
                settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET, order.razorpay_order_id
            )
            if payment_id:
                applied |= PlatformService.complete_checkout(order.razorpay_order_id, payment_id).status == (
                    CheckoutStatus.PAID
                )
            elif order.created_at < cutoff:
                SaasCheckoutOrder.objects.filter(id=order.id, status=CheckoutStatus.CREATED).update(
                    status=CheckoutStatus.EXPIRED
                )
        return applied

    @staticmethod
    def complete_checkout(razorpay_order_id, payment_id):
        """Record the payment for a paid order — once, whether from Checkout, webhook or reconcile."""
        with transaction.atomic():
            order = (
                SaasCheckoutOrder.objects.select_for_update()
                .select_related("saas_subscription")
                .get(razorpay_order_id=razorpay_order_id)
            )
            if order.status in (CheckoutStatus.PAID, CheckoutStatus.FAILED):
                return order
            order.razorpay_payment_id = payment_id
            try:
                order.payment = PlatformService.record_manual_payment(
                    order.saas_subscription,
                    amount=order.amount,
                    method=PaymentMethod.RAZORPAY,
                    reference=payment_id,
                    razorpay_payment_id=payment_id,
                    razorpay_order_id=razorpay_order_id,
                )
                order.status = CheckoutStatus.PAID
            except ValueError as e:
                order.status = CheckoutStatus.FAILED
                order.failure_reason = (
                    f"₹{order.amount} was received (Razorpay {payment_id}) but could not be applied: {e} "
                    "Please contact support."
                )[:255]
                logger.error("SaaS payment %s for order %s not applied: %s", payment_id, order.id, e)
            order.save()
        return order

    @staticmethod
    @transaction.atomic
    def cancel_subscription(subscription, today=None):
        """Cancel the monthly plan. Access continues until the paid month ends."""
        today = today or timezone.now().date()
        if subscription.status in (SaasStatus.CANCELLED, SaasStatus.SUSPENDED):
            raise ValueError(f"Cannot cancel a {subscription.status.lower()} subscription.")

        subscription.status = SaasStatus.CANCELLED
        subscription.cancelled_at = timezone.now()
        subscription.save(update_fields=["status", "cancelled_at", "updated_at"])

        end = subscription.current_period_end
        if end is None or end <= today:
            PlatformService.suspend_business(subscription.business)
        return subscription

    @staticmethod
    def run_billing_checks(today=None):
        """Nightly: move overdue businesses along ACTIVE → PAST_DUE → SUSPENDED.

        - ACTIVE on/after its due date → PAST_DUE (grace period starts)
        - PAST_DUE for GRACE_DAYS → SUSPENDED
        - CANCELLED once the paid month ends → business access suspended
        - PENDING (first payment never made) for GRACE_DAYS after onboarding → SUSPENDED
        - legacy TRIAL past its end date → SUSPENDED
        """
        today = today or timezone.now().date()
        counts = {"past_due": 0, "suspended": 0}

        counts["past_due"] = SaasSubscription.objects.filter(
            status=SaasStatus.ACTIVE, current_period_end__lte=today
        ).update(status=SaasStatus.PAST_DUE)

        to_suspend = list(
            SaasSubscription.objects.filter(
                status=SaasStatus.PAST_DUE, current_period_end__lte=today - timedelta(days=GRACE_DAYS)
            ).select_related("business")
        )
        to_suspend += SaasSubscription.objects.filter(
            status=SaasStatus.CANCELLED, current_period_end__lte=today, business__status=Status.ACTIVE
        ).select_related("business")
        to_suspend += SaasSubscription.objects.filter(
            status=SaasStatus.TRIAL, trial_end_date__lt=today
        ).select_related("business")
        to_suspend += SaasSubscription.objects.filter(
            status=SaasStatus.PENDING,
            setup_fee_paid=False,
            created_at__date__lte=today - timedelta(days=GRACE_DAYS),
            business__status=Status.ACTIVE,
        ).select_related("business")

        for sub in to_suspend:
            PlatformService.suspend_business(sub.business)
            counts["suspended"] += 1

        logger.info("Billing checks: %(past_due)d past due, %(suspended)d suspended", counts)
        return counts

    @staticmethod
    @transaction.atomic
    def activate_subscription(subscription, plan, razorpay_subscription_id="", razorpay_customer_id=""):
        """Transition to ACTIVE with a paid plan."""
        subscription.plan = plan
        subscription.status = SaasStatus.ACTIVE
        subscription.current_period_start = timezone.now().date()
        subscription.current_period_end = timezone.now().date() + timedelta(days=30)
        subscription.payment_failure_count = 0
        if razorpay_subscription_id:
            subscription.razorpay_subscription_id = razorpay_subscription_id
        if razorpay_customer_id:
            subscription.razorpay_customer_id = razorpay_customer_id
        subscription.save()
        return subscription

    @staticmethod
    @transaction.atomic
    def record_payment_success(subscription, amount, razorpay_payment_id="", razorpay_order_id=""):
        """Record successful payment, reset failure count, ensure ACTIVE."""
        payment = SaasPayment.objects.create(
            saas_subscription=subscription,
            business=subscription.business,
            plan=subscription.plan,
            amount=amount,
            status=PaymentStatus.PAID,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_order_id=razorpay_order_id,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
        )
        subscription.payment_failure_count = 0
        subscription.status = SaasStatus.ACTIVE
        # Advance period
        subscription.current_period_start = timezone.now().date()
        subscription.current_period_end = timezone.now().date() + timedelta(days=30)
        subscription.save()
        return payment

    @staticmethod
    @transaction.atomic
    def record_payment_failure(subscription, amount, failure_reason="", razorpay_payment_id=""):
        """Record failed payment, increment failure count, suspend after MAX_PAYMENT_FAILURES."""
        SaasPayment.objects.create(
            saas_subscription=subscription,
            business=subscription.business,
            plan=subscription.plan,
            amount=amount,
            status=PaymentStatus.FAILED,
            razorpay_payment_id=razorpay_payment_id,
            failure_reason=failure_reason,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
        )
        subscription.payment_failure_count += 1
        if subscription.payment_failure_count >= MAX_PAYMENT_FAILURES:
            PlatformService.suspend_business(subscription.business)
        else:
            subscription.status = SaasStatus.PAST_DUE
            subscription.save()

    @staticmethod
    @transaction.atomic
    def suspend_business(business):
        """Suspend the Business. A CANCELLED subscription stays CANCELLED (owner's choice)."""
        business.status = Status.SUSPENDED
        business.save(update_fields=["status"])

        try:
            sub = business.saas_subscription
            if sub.status != SaasStatus.CANCELLED:
                sub.status = SaasStatus.SUSPENDED
                sub.save(update_fields=["status"])
        except SaasSubscription.DoesNotExist:
            pass

        logger.info("Business %s suspended", business.id)

    @staticmethod
    @transaction.atomic
    def reactivate_business(business, today=None):
        """SUPER_ADMIN override: restore access without a payment.

        Refused when the setup fee is unpaid or the reactivation fee applies — those
        businesses come back only through record_manual_payment, so the fees can't be skipped.
        Otherwise billing status follows the dates: if the paid month is over, the business is
        PAST_DUE again and the nightly check re-suspends it after the grace period.
        """
        today = today or timezone.now().date()
        sub = getattr(business, "saas_subscription", None)
        if sub is not None:
            due = PlatformService.amount_due(sub, today)
            if due.setup_fee or due.reactivation_fee:
                raise ValueError(
                    f"₹{due.total} is due (includes "
                    + ("the setup fee" if due.setup_fee else "the reactivation fee")
                    + "). Record the payment to restore access."
                )
        business.status = Status.ACTIVE
        business.save(update_fields=["status"])

        try:
            sub = business.saas_subscription
        except SaasSubscription.DoesNotExist:
            PlatformService.start_billing(business)
        else:
            if sub.current_period_end and sub.current_period_end > today:
                sub.status = SaasStatus.ACTIVE
            elif sub.setup_fee_paid:
                sub.status = SaasStatus.PAST_DUE
            else:
                sub.status = SaasStatus.PENDING
            sub.cancelled_at = None
            sub.payment_failure_count = 0
            sub.save()

        logger.info("Business %s reactivated", business.id)

    @staticmethod
    def get_platform_stats():
        """Platform-wide stats for SUPER_ADMIN dashboard."""
        from django.db.models import Count, Sum

        total = Business.objects.count()
        active = Business.objects.filter(status=Status.ACTIVE).count()
        suspended = Business.objects.filter(status=Status.SUSPENDED).count()
        trials = SaasSubscription.objects.filter(status=SaasStatus.TRIAL).count()
        pending = SaasSubscription.objects.filter(status=SaasStatus.PENDING).count()
        past_due = SaasSubscription.objects.filter(status=SaasStatus.PAST_DUE).count()
        paid = SaasSubscription.objects.filter(status=SaasStatus.ACTIVE).count()

        revenue = (
            SaasPayment.objects.filter(status=PaymentStatus.PAID).aggregate(total=Sum("amount"))["total"] or 0
        )

        plans_breakdown = (
            SaasSubscription.objects.filter(plan__isnull=False)
            .values("plan__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        return {
            "total_businesses": total,
            "active_businesses": active,
            "suspended_businesses": suspended,
            "trial_businesses": trials,
            "pending_businesses": pending,
            "past_due_businesses": past_due,
            "paid_businesses": paid,
            "total_revenue": str(revenue),
            "plans_breakdown": list(plans_breakdown),
        }
