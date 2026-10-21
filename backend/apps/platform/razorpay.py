"""Thin Razorpay client wrapper — isolates SDK calls for testability."""

import hashlib
import hmac
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def _get_client():
    import razorpay

    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
    )


class RazorpayClient:
    @staticmethod
    def create_customer(name, email, contact=""):
        client = _get_client()
        return client.customer.create(
            data={"name": name, "email": email, "contact": contact},
        )

    @staticmethod
    def create_subscription(plan_id, customer_id, total_count=12):
        client = _get_client()
        return client.subscription.create(
            data={
                "plan_id": plan_id,
                "customer_id": customer_id,
                "total_count": total_count,
                "customer_notify": 1,
            },
        )

    @staticmethod
    def cancel_subscription(subscription_id, cancel_at_cycle_end=False):
        client = _get_client()
        return client.subscription.cancel(
            subscription_id,
            data={"cancel_at_cycle_end": cancel_at_cycle_end},
        )

    @staticmethod
    def verify_webhook_signature(body, signature):
        """HMAC-SHA256 verification of Razorpay webhook payload."""
        secret = settings.RAZORPAY_WEBHOOK_SECRET
        expected = hmac.new(
            secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
