"""Razorpay Checkout (Orders API) helpers shared by customer and platform payments.

Keys are passed in explicitly: customer payments use the business's own keys,
platform billing uses the platform keys from settings.
"""

import hashlib
import hmac
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

CHECKOUT_SCRIPT_URL = "https://checkout.razorpay.com/v1/checkout.js"


class CheckoutError(Exception):
    """Razorpay could not be reached or rejected the request."""


def to_paise(amount: Decimal) -> int:
    return int((Decimal(amount) * 100).to_integral_value())


def _client(key_id, key_secret):
    import razorpay

    return razorpay.Client(auth=(key_id, key_secret))


def create_order(key_id, key_secret, *, amount, receipt, notes=None):
    """Create an order for `amount` rupees. Returns the Razorpay order dict."""
    try:
        return _client(key_id, key_secret).order.create(
            data={
                "amount": to_paise(amount),
                "currency": "INR",
                "receipt": receipt[:40],
                "payment_capture": 1,
                "notes": notes or {},
            }
        )
    except Exception as e:  # SDK raises BadRequestError/ServerError/requests errors
        logger.warning("Razorpay order creation failed: %s", e)
        raise CheckoutError("Could not start the payment. Please try again in a minute.") from e


def fetch_captured_payment_id(key_id, key_secret, order_id):
    """ID of a captured payment for this order, or None. Used when the browser never confirmed."""
    try:
        payments = _client(key_id, key_secret).order.payments(order_id)
    except Exception as e:
        logger.warning("Razorpay order lookup failed for %s: %s", order_id, e)
        return None
    for p in payments.get("items", []):
        if p.get("status") == "captured":
            return p.get("id")
    return None


def verify_payment_signature(key_secret, order_id, payment_id, signature):
    """Checkout success handler signature: HMAC-SHA256(order_id|payment_id, key_secret)."""
    if not (key_secret and order_id and payment_id and signature):
        return False
    expected = hmac.new(
        key_secret.encode("utf-8"), f"{order_id}|{payment_id}".encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
