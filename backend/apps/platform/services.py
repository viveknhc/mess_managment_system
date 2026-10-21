"""Platform billing business logic — thin views call these methods."""

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.businesses.models import Business
from apps.platform.models import (
    PaymentStatus,
    SaasPayment,
    SaasStatus,
    SaasSubscription,
)
from common.constants import Status

logger = logging.getLogger(__name__)

TRIAL_DAYS = 30
MAX_PAYMENT_FAILURES = 3


class PlatformService:
    @staticmethod
    @transaction.atomic
    def start_trial(business):
        """Create SaasSubscription in TRIAL status with 30-day end date."""
        sub, created = SaasSubscription.objects.get_or_create(
            business=business,
            defaults={
                "status": SaasStatus.TRIAL,
                "trial_end_date": timezone.now().date() + timedelta(days=TRIAL_DAYS),
            },
        )
        if not created:
            logger.info("SaasSubscription already exists for business %s", business.id)
        return sub

    @staticmethod
    @transaction.atomic
    def register_business(
        *, name, owner_username, owner_password, owner_name="", owner_email="", owner_phone=""
    ):
        """Self-serve signup: create Business + Owner + default meals + start trial."""
        from apps.accounts.models import User
        from apps.meals.models import Meal
        from common.constants import Role

        business = Business.objects.create(name=name, status=Status.ACTIVE)
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
        for meal_name in ["Breakfast", "Lunch", "Dinner", "Snacks"]:
            Meal.objects.create(business=business, name=meal_name)
        PlatformService.start_trial(business)
        return business, user

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
        """Suspend both SaasSubscription and Business."""
        business.status = Status.SUSPENDED
        business.save(update_fields=["status"])

        try:
            sub = business.saas_subscription
            sub.status = SaasStatus.SUSPENDED
            sub.save(update_fields=["status"])
        except SaasSubscription.DoesNotExist:
            pass

        logger.info("Business %s suspended", business.id)

    @staticmethod
    @transaction.atomic
    def reactivate_business(business, *, extend_trial_days=0):
        """SUPER_ADMIN reactivates a suspended business."""
        business.status = Status.ACTIVE
        business.save(update_fields=["status"])

        try:
            sub = business.saas_subscription
            if extend_trial_days > 0:
                sub.status = SaasStatus.TRIAL
                sub.trial_end_date = timezone.now().date() + timedelta(days=extend_trial_days)
            elif sub.plan:
                sub.status = SaasStatus.ACTIVE
            else:
                sub.status = SaasStatus.TRIAL
                sub.trial_end_date = timezone.now().date() + timedelta(days=TRIAL_DAYS)
            sub.payment_failure_count = 0
            sub.save()
        except SaasSubscription.DoesNotExist:
            PlatformService.start_trial(business)

        logger.info("Business %s reactivated", business.id)

    @staticmethod
    def get_platform_stats():
        """Platform-wide stats for SUPER_ADMIN dashboard."""
        from django.db.models import Count, Sum

        total = Business.objects.count()
        active = Business.objects.filter(status=Status.ACTIVE).count()
        suspended = Business.objects.filter(status=Status.SUSPENDED).count()
        trials = SaasSubscription.objects.filter(status=SaasStatus.TRIAL).count()
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
            "paid_businesses": paid,
            "total_revenue": str(revenue),
            "plans_breakdown": list(plans_breakdown),
        }
