"""Payment model (PAY-01)."""

from django.core.validators import MinValueValidator
from django.db import models

from common.models import TenantScopedModel


class PaymentMethod:
    CASH = "CASH"
    UPI = "UPI"
    BANK_TRANSFER = "BANK_TRANSFER"
    CARD = "CARD"
    ONLINE = "ONLINE"
    OTHER = "OTHER"


PAYMENT_METHOD_CHOICES = [
    (PaymentMethod.CASH, "Cash"),
    (PaymentMethod.UPI, "UPI"),
    (PaymentMethod.BANK_TRANSFER, "Bank Transfer"),
    (PaymentMethod.CARD, "Card"),
    (PaymentMethod.ONLINE, "Online"),
    (PaymentMethod.OTHER, "Other"),
]


class PaymentStatus:
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


PAYMENT_STATUS_CHOICES = [
    (PaymentStatus.PAID, "Paid"),
    (PaymentStatus.FAILED, "Failed"),
    (PaymentStatus.REFUNDED, "Refunded"),
]


class Payment(TenantScopedModel):
    """A payment recorded against a subscription."""

    subscription = models.ForeignKey(
        "subscriptions.Subscription", on_delete=models.CASCADE, related_name="payments"
    )
    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default=PaymentMethod.CASH)
    transaction_reference = models.CharField(max_length=200, blank=True)
    payment_date = models.DateField()
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default=PaymentStatus.PAID)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-payment_date", "-created_at"]
        indexes = [
            models.Index(fields=["subscription"], name="idx_payment_subscription"),
        ]

    def __str__(self):
        return f"₹{self.amount} — {self.customer} ({self.status})"
