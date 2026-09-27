"""Subscription serializers (S-05)."""

import datetime

from rest_framework import serializers

from apps.customers.models import Customer
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription


class SubscriptionListSerializer(serializers.ModelSerializer):
    """Read-only for list view."""

    customer_name = serializers.CharField(source="customer.name", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    remaining_days = serializers.IntegerField(read_only=True)
    is_expiring = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "customer",
            "customer_name",
            "plan",
            "plan_name",
            "start_date",
            "end_date",
            "status",
            "total_amount",
            "paid_amount",
            "pending_amount",
            "remaining_meals",
            "remaining_days",
            "is_expiring",
            "renewed_from",
            "created_at",
        ]
        read_only_fields = fields


class SubscriptionDetailSerializer(SubscriptionListSerializer):
    """Full detail — same fields plus updated_at."""

    class Meta(SubscriptionListSerializer.Meta):
        fields = SubscriptionListSerializer.Meta.fields + ["updated_at"]
        read_only_fields = fields


class SubscriptionCreateSerializer(serializers.Serializer):
    """Create a subscription. Delegates to SubscriptionService."""

    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.all())
    start_date = serializers.DateField(default=datetime.date.today)

    def validate_customer(self, value):
        business_id = self.context["request"].user.business_id
        if value.business_id != business_id:
            raise serializers.ValidationError("Customer not found.")
        return value

    def validate_plan(self, value):
        business_id = self.context["request"].user.business_id
        if value.business_id != business_id:
            raise serializers.ValidationError("Plan not found.")
        if not value.is_active:
            raise serializers.ValidationError("Cannot subscribe to an inactive plan.")
        return value

    def validate_start_date(self, value):
        if value < datetime.date.today():
            raise serializers.ValidationError("Start date cannot be in the past.")
        return value
