"""SaaS billing models — plan catalog, per-business subscriptions, payment history.

Billing follows docs/Monthly_Subscription_Plan.pdf: one-time setup fee + monthly fee,
first payment = setup + first month, cancel any time, reactivation fee after a long gap.
"""

from django.db import models

from common.models import TimeStampedModel, UUIDModel


class SaasStatus:
    PENDING = "PENDING"  # created, first payment (setup + first month) not yet received
    TRIAL = "TRIAL"  # legacy — free trials are no longer offered
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"


SAAS_STATUS_CHOICES = [
    (SaasStatus.PENDING, "Awaiting First Payment"),
    (SaasStatus.TRIAL, "Trial"),
    (SaasStatus.ACTIVE, "Active"),
    (SaasStatus.PAST_DUE, "Past Due"),
    (SaasStatus.SUSPENDED, "Suspended"),
    (SaasStatus.CANCELLED, "Cancelled"),
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


class PaymentMethod:
    UPI = "UPI"
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"
    RAZORPAY = "RAZORPAY"


PAYMENT_METHOD_CHOICES = [
    (PaymentMethod.UPI, "UPI"),
    (PaymentMethod.CASH, "Cash"),
    (PaymentMethod.BANK_TRANSFER, "Bank Transfer"),
    (PaymentMethod.RAZORPAY, "Razorpay"),
]


class SaasPlan(UUIDModel, TimeStampedModel):
    """Pricing tier catalog — managed by SUPER_ADMIN."""

    name = models.CharField(max_length=100)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    setup_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, help_text="One-time, non-refundable"
    )
    reactivation_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, help_text="Charged when returning after a long gap"
    )
    max_customers = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    max_staff = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    features = models.JSONField(default=list, blank=True, help_text="Human-readable feature list")
    razorpay_plan_id = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["price_monthly"]

    def __str__(self):
        return f"{self.name} — ₹{self.price_monthly}/mo"


class SaasSubscription(UUIDModel, TimeStampedModel):
    """One per Business — tracks billing status and Razorpay subscription."""

    business = models.OneToOneField(
        "businesses.Business",
        on_delete=models.CASCADE,
        related_name="saas_subscription",
    )
    plan = models.ForeignKey(SaasPlan, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=SAAS_STATUS_CHOICES, default=SaasStatus.PENDING)
    setup_fee_paid = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    trial_end_date = models.DateField(null=True, blank=True)
    current_period_start = models.DateField(null=True, blank=True)
    # First day NOT covered by the last payment — the next monthly fee is due on this date.
    current_period_end = models.DateField(null=True, blank=True)

    razorpay_subscription_id = models.CharField(max_length=100, blank=True)
    razorpay_customer_id = models.CharField(max_length=100, blank=True)

    payment_failure_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.business.name} — {self.status}"


class SaasPayment(UUIDModel, TimeStampedModel):
    """Immutable billing history — one row per payment (recorded by SUPER_ADMIN or Razorpay)."""

    saas_subscription = models.ForeignKey(SaasSubscription, on_delete=models.CASCADE, related_name="payments")
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE)
    plan = models.ForeignKey(SaasPlan, null=True, blank=True, on_delete=models.SET_NULL)

    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total received")
    # Breakdown of amount: amount = setup_fee + reactivation_fee + monthly fee
    setup_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reactivation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES)
    method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default=PaymentMethod.RAZORPAY)
    reference = models.CharField(max_length=100, blank=True, help_text="UPI / bank reference")
    recorded_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True)

    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.business.name} — ₹{self.amount} ({self.status})"
