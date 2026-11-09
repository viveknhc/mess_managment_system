"""Celery tasks for notifications (N-04)."""

import logging

from config.celery import app

logger = logging.getLogger(__name__)


@app.task
def send_expiring_notifications_task():
    """Nightly: in-app expiring notifications + daily expiry emails, per business.

    Each business is processed independently — a failure in one is logged and
    does not stop the others.
    """
    from apps.businesses.models import Business
    from apps.notifications.services import NotificationService

    total = 0
    emails = 0
    for biz in Business.objects.filter(status="ACTIVE"):
        try:
            total += NotificationService.emit_expiring_notifications(biz.id)
        except Exception:
            logger.exception("In-app expiring notifications failed for business %s", biz.id)
        try:
            emails += NotificationService.send_expiry_emails(biz.id)
        except Exception:
            logger.exception("Expiry emails failed for business %s", biz.id)

    logger.info("Sent %d expiring notifications and %d expiry emails", total, emails)
    return total
