"""Celery tasks for notifications (N-04)."""

import logging

from config.celery import app

logger = logging.getLogger(__name__)


@app.task
def send_expiring_notifications_task():
    """Nightly: send expiring subscription notifications to all business owners."""
    from apps.businesses.models import Business
    from apps.notifications.services import NotificationService

    total = 0
    for biz in Business.objects.filter(status="ACTIVE"):
        count = NotificationService.emit_expiring_notifications(biz.id)
        total += count

    logger.info("Sent %d expiring notifications", total)
    return total
