"""Celery tasks for subscriptions.

Daily job (schedule shortly after midnight, before
apps.deliveries.tasks.generate_next_day_deliveries_task):
- process_pause_windows_task: start/end pause windows (ACTIVE↔PAUSED),
  restore deliveries and extend end_date for paused meals.
"""

import logging

from config.celery import app

logger = logging.getLogger(__name__)


@app.task
def process_pause_windows_task():
    from apps.subscriptions.services import SubscriptionService

    result = SubscriptionService.process_pause_windows()
    logger.info("Pause windows: %(started)d started, %(ended)d ended", result)
    return result
