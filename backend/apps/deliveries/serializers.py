"""Delivery serializers (D-04, D-05, D-06)."""

from rest_framework import serializers

from apps.deliveries.models import DELIVERY_STATUS_CHOICES, Delivery, MealSkip, SubscriptionPause


class DeliveryListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    customer_address = serializers.CharField(source="customer.address", read_only=True)
    meal_name = serializers.CharField(source="meal.name", read_only=True)
    assigned_staff_name = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields = [
            "id",
            "subscription",
            "customer",
            "customer_name",
            "customer_phone",
            "customer_address",
            "meal",
            "meal_name",
            "delivery_date",
            "status",
            "assigned_staff",
            "assigned_staff_name",
            "delivered_at",
            "notes",
        ]
        read_only_fields = fields

    def get_assigned_staff_name(self, obj):
        if obj.assigned_staff:
            return obj.assigned_staff.name or obj.assigned_staff.username
        return None


class DeliveryStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=DELIVERY_STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class MealSkipSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealSkip
        fields = ["id", "subscription", "customer", "delivery", "skip_date", "reason", "created_at"]
        read_only_fields = fields


class SubscriptionPauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPause
        fields = ["id", "subscription", "start_date", "end_date", "reason", "created_at"]
        read_only_fields = fields
