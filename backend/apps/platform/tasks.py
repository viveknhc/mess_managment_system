"""Celery beat tasks for SaaS billing — trial expiration and past-due checks."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def check_trial_expirations():
    """Suspend businesses whose trial has expired. Runs nightly at 00:05."""
    from apps.platform.models import SaasStatus, SaasSubscription
    from apps.platform.services import PlatformService

    today = timezone.now().date()
    expired = SaasSubscription.objects.filter(
        status=SaasStatus.TRIAL,
        trial_end_date__lt=today,
    ).select_related("business")

    count = 0
    for sub in expired:
        PlatformService.suspend_business(sub.business)
        count += 1

    logger.info("Trial expiration check: %d businesses suspended", count)
    return count


@shared_task
def check_past_due_subscriptions():
    """Suspend PAST_DUE subscriptions older than 7 days. Runs nightly at 00:10."""
    from datetime import timedelta

    from apps.platform.models import SaasStatus, SaasSubscription
    from apps.platform.services import PlatformService

    cutoff = timezone.now() - timedelta(days=7)
    past_due = SaasSubscription.objects.filter(
        status=SaasStatus.PAST_DUE,
        updated_at__lt=cutoff,
    ).select_related("business")

    count = 0
    for sub in past_due:
        PlatformService.suspend_business(sub.business)
        count += 1

    logger.info("Past-due check: %d businesses suspended", count)
    return count
