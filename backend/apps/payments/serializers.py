"""Payment serializers (PAY-05)."""

import datetime
from decimal import Decimal

from rest_framework import serializers

from apps.payments.models import PAYMENT_METHOD_CHOICES, Payment, UpiPaymentClaim
from apps.subscriptions.models import Subscription


class PaymentListSerializer(serializers.ModelSerializer):
    """Read-only for payment list."""

    customer_name = serializers.CharField(source="customer.name", read_only=True)
    subscription_plan = serializers.CharField(source="subscription.plan.name", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "subscription",
            "customer",
            "customer_name",
            "subscription_plan",
            "amount",
            "method",
            "transaction_reference",
            "payment_date",
            "status",
            "notes",
            "created_at",
        ]
        read_only_fields = fields


class PaymentCreateSerializer(serializers.Serializer):
    """Create a payment. Delegates to PaymentService."""

    subscription = serializers.PrimaryKeyRelatedField(queryset=Subscription.objects.all())
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    method = serializers.ChoiceField(choices=PAYMENT_METHOD_CHOICES)
    payment_date = serializers.DateField(default=datetime.date.today)
    transaction_reference = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_subscription(self, value):
        business_id = self.context["request"].user.business_id
        if value.business_id != business_id:
            raise serializers.ValidationError("Subscription not found.")
        return value


class UpiClaimSerializer(serializers.ModelSerializer):
    """A customer's "I've paid by UPI", for the owner to confirm or reject. Read-only."""

    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    subscription_plan = serializers.CharField(source="subscription.plan.name", read_only=True)
    subscription_status = serializers.CharField(source="subscription.status", read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = UpiPaymentClaim
        fields = [
            "id",
            "subscription",
            "customer",
            "customer_name",
            "customer_phone",
            "subscription_plan",
            "subscription_status",
            "amount",
            "utr",
            "status",
            "payment",
            "reject_reason",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_reviewed_by_name(self, obj):
        u = obj.reviewed_by
        return (u.name or u.username) if u else ""
