"""Subscription serializers (S-05)."""

import datetime

from rest_framework import serializers

from apps.customers.models import Customer
from apps.deliveries.serializers import SubscriptionPauseSerializer
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription, SubscriptionItem


class SubscriptionItemSerializer(serializers.ModelSerializer):
    label = serializers.CharField(max_length=120)
    price_per_meal = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, default=0)

    class Meta:
        model = SubscriptionItem
        fields = ["label", "price_per_meal"]


class SubscriptionListSerializer(serializers.ModelSerializer):
    """Read-only for list view."""

    items = SubscriptionItemSerializer(many=True, read_only=True)
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
            "custom_price",
            "items",
            "created_at",
        ]
        read_only_fields = fields


class SubscriptionDetailSerializer(SubscriptionListSerializer):
    """Full detail — same fields plus updated_at and pause windows."""

    pauses = SubscriptionPauseSerializer(many=True, read_only=True)

    class Meta(SubscriptionListSerializer.Meta):
        fields = SubscriptionListSerializer.Meta.fields + ["updated_at", "pauses"]
        read_only_fields = fields


class PauseRequestSerializer(serializers.Serializer):
    """Owner/manager pause body. All optional: no body = open-ended pause from today."""

    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class SubscriptionCreateSerializer(serializers.Serializer):
    """Create a subscription. Delegates to SubscriptionService."""

    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.all())
    start_date = serializers.DateField(default=datetime.date.today)
    # Feature custom_subscriptions — the view rejects these when it's off.
    custom_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False, allow_null=True, default=None
    )
    items = SubscriptionItemSerializer(many=True, required=False, default=list)

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


class SubscriptionCustomizeSerializer(serializers.Serializer):
    """Body of POST /subscriptions/{id}/customize/. ``items`` is the full list;
    ``custom_price`` (omit to keep, null = plan price) only before the subscription starts."""

    items = SubscriptionItemSerializer(many=True)
    custom_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False, allow_null=True
    )
