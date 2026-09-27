"""Subscription business logic (S-04, S-06, S-07, S-08, S-09).

Thin views call these; all writes happen here inside transactions.
"""

import datetime
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q

from apps.subscriptions.models import Subscription
from common.constants import SubStatus


class SubscriptionService:
    @staticmethod
    @transaction.atomic
    def create_subscription(*, business_id, customer, plan, start_date):
        """Create a PENDING subscription from a plan.

        Validates customer and plan belong to the same business.
        """
        if customer.business_id != business_id:
            raise ValueError("Customer does not belong to this business.")
        if plan.business_id != business_id:
            raise ValueError("Plan does not belong to this business.")
        if not plan.is_active:
            raise ValueError("Cannot subscribe to an inactive plan.")

        end_date = start_date + timedelta(days=plan.duration_days)

        return Subscription.objects.create(
            business_id=business_id,
            customer=customer,
            plan=plan,
            start_date=start_date,
            end_date=end_date,
            status=SubStatus.PENDING,
            total_amount=plan.price,
            paid_amount=Decimal("0.00"),
            pending_amount=plan.price,
            remaining_meals=plan.total_meals,
        )

    @staticmethod
    @transaction.atomic
    def pause(subscription):
        """Pause an ACTIVE subscription."""
        subscription.transition_to(SubStatus.PAUSED)
        subscription.save(update_fields=["status", "updated_at"])
        return subscription

    @staticmethod
    @transaction.atomic
    def resume(subscription):
        """Resume a PAUSED subscription."""
        subscription.transition_to(SubStatus.ACTIVE)
        subscription.save(update_fields=["status", "updated_at"])
        return subscription

    @staticmethod
    @transaction.atomic
    def cancel(subscription):
        """Cancel a PENDING or ACTIVE subscription."""
        subscription.transition_to(SubStatus.CANCELLED)
        subscription.save(update_fields=["status", "updated_at"])
        return subscription

    @staticmethod
    @transaction.atomic
    def renew(subscription, *, start_date=None):
        """Renew an EXPIRED or CANCELLED subscription.

        Creates a new PENDING subscription linked via renewed_from.
        The old subscription is untouched.
        """
        if subscription.status not in (SubStatus.EXPIRED, SubStatus.CANCELLED):
            raise ValueError(f"Can only renew EXPIRED or CANCELLED subscriptions, got {subscription.status}")

        plan = subscription.plan
        if not plan.is_active:
            raise ValueError("Cannot renew with an inactive plan.")

        new_start = start_date or datetime.date.today()
        new_end = new_start + timedelta(days=plan.duration_days)

        return Subscription.objects.create(
            business_id=subscription.business_id,
            customer=subscription.customer,
            plan=plan,
            start_date=new_start,
            end_date=new_end,
            status=SubStatus.PENDING,
            total_amount=plan.price,
            paid_amount=Decimal("0.00"),
            pending_amount=plan.price,
            remaining_meals=plan.total_meals,
            renewed_from=subscription,
        )


class SubscriptionSelector:
    @staticmethod
    def get_expiring(business_id, days_ahead=3):
        """EXPIRING = ACTIVE and end_date within N days. Never stored."""
        today = datetime.date.today()
        return Subscription.objects.filter(
            Q(business_id=business_id)
            & Q(status=SubStatus.ACTIVE)
            & Q(end_date__gte=today)
            & Q(end_date__lte=today + timedelta(days=days_ahead))
        )
