"""Delivery serializers (D-04, D-05, D-06)."""

from rest_framework import serializers

from apps.accounts.models import User
from apps.deliveries.models import (
    DELIVERY_STATUS_CHOICES,
    Delivery,
    DeliveryRoute,
    MealSkip,
    SubscriptionPause,
)


class DeliveryListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    customer_address = serializers.CharField(source="customer.address", read_only=True)
    meal_name = serializers.CharField(source="meal.name", read_only=True)
    assigned_staff_name = serializers.SerializerMethodField()
    route_name = serializers.CharField(source="customer.route.name", read_only=True, default=None)
    customizations = serializers.SerializerMethodField()

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
            "route_name",
            "customizations",
            "delivered_at",
            "notes",
            "updated_at",  # lets the app hide Undo once UNDO_WINDOW has passed
        ]
        read_only_fields = fields

    def get_assigned_staff_name(self, obj):
        if obj.assigned_staff:
            return obj.assigned_staff.name or obj.assigned_staff.username
        return None

    def get_customizations(self, obj):
        """The subscription's food customizations, e.g. ["Extra chicken 100g", "No rice"]."""
        return [item.label for item in obj.subscription.items.all()]


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
        fields = [
            "id",
            "subscription",
            "start_date",
            "end_date",
            "reason",
            "resumed_on",
            "is_closed",
            "days_extended",
            "created_at",
        ]
        read_only_fields = fields


class DeliveryRouteSerializer(serializers.ModelSerializer):
    """Read + write a route. ``customer_ids`` (write) = the route's full customer list."""

    staff = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), allow_null=True, required=False, default=None
    )
    staff_name = serializers.SerializerMethodField()
    customer_ids = serializers.ListField(child=serializers.UUIDField(), required=False, write_only=True)
    customer_count = serializers.IntegerField(read_only=True, default=0)
    customers = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryRoute
        fields = [
            "id",
            "name",
            "staff",
            "staff_name",
            "notes",
            "customer_ids",
            "customer_count",
            "customers",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Route name is required.")
        return value

    def get_staff_name(self, obj):
        return (obj.staff.name or obj.staff.username) if obj.staff else None

    def get_customers(self, obj):
        return [
            {"id": str(c.id), "name": c.name, "customer_code": c.customer_code, "location": c.location}
            for c in obj.customers.all()
        ]
