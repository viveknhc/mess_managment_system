"""Celery beat task for SaaS billing — overdue and cancelled subscriptions."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def run_billing_checks():
    """Mark overdue businesses PAST_DUE, suspend them after the grace period. Runs nightly."""
    from apps.platform.services import PlatformService

    return PlatformService.run_billing_checks()
