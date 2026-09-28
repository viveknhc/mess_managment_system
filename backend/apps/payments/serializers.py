"""Payment serializers (PAY-05)."""

import datetime
from decimal import Decimal

from rest_framework import serializers

from apps.payments.models import PAYMENT_METHOD_CHOICES, Payment
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
