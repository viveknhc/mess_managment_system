"""Celery Beat tasks for deliveries (D-13, D-14).

Nightly jobs:
- generate_next_day_deliveries: create PENDING rows for tomorrow
- expire_subscriptions: mark past-end-date ACTIVE subs as EXPIRED
"""

import logging

from config.celery import app

logger = logging.getLogger(__name__)


@app.task
def expire_subscriptions_task():
    """Nightly: mark ACTIVE subscriptions past end_date as EXPIRED."""
    from apps.deliveries.services import DeliverySelector

    count = DeliverySelector.expire_subscriptions()
    logger.info("Expired %d subscriptions", count)
    return count


@app.task
def generate_next_day_deliveries_task():
    """Nightly: generate delivery rows for tomorrow for all ACTIVE subscriptions."""
    import datetime

    from apps.deliveries.services import DeliveryService
    from apps.subscriptions.models import Subscription
    from common.constants import SubStatus

    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    active_subs = Subscription.objects.filter(
        status=SubStatus.ACTIVE,
        start_date__lte=tomorrow,
        end_date__gte=tomorrow,
    ).select_related("plan__meal", "customer")

    total = 0
    for sub in active_subs:
        deliveries = DeliveryService.generate_delivery_schedule(sub)
        total += len(deliveries)

    logger.info("Generated %d deliveries for %s", total, tomorrow)
    return total
