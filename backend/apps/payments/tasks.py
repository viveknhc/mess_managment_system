"""Celery tasks for payments.

Daily job:
- reconcile_online_payments_task: apply customer online payments that neither the
  Checkout success nor the webhook delivered.
"""

import logging

from config.celery import app

logger = logging.getLogger(__name__)


@app.task
def reconcile_online_payments_task():
    from apps.payments.services import OnlinePaymentService

    count = OnlinePaymentService.reconcile_all()
    logger.info("Reconciled online payment orders for %d subscriptions", count)
    return count
