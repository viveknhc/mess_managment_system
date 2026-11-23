"""Customer serializers (C-03)."""

from rest_framework import serializers

from apps.customers.models import Customer
from apps.customization.registry import DELIVERY_ROUTES
from apps.customization.services import FeatureService
from common.constants import Status

CUSTOMER_STATUS_CHOICES = [
    (Status.ACTIVE, "Active"),
    (Status.INACTIVE, "Inactive"),
    (Status.BLOCKED, "Blocked"),
]


def _validate_route(serializer, value):
    """A route must belong to the caller's business, and routes must be enabled for it."""
    if value is None:
        return value
    business_id = serializer.context["request"].user.business_id
    if value.business_id != business_id:
        raise serializers.ValidationError("Route not found.")
    if not FeatureService.has(business_id, DELIVERY_ROUTES):
        raise serializers.ValidationError("Delivery routes are not enabled for this business.")
    return value


class CustomerListSerializer(serializers.ModelSerializer):
    """Read-only serializer for customer list."""

    route_name = serializers.CharField(source="route.name", read_only=True, default=None)

    class Meta:
        model = Customer
        fields = [
            "id",
            "customer_code",
            "name",
            "phone",
            "email",
            "status",
            "location",
            "route",
            "route_name",
            "created_at",
        ]
        read_only_fields = fields


class CustomerDetailSerializer(serializers.ModelSerializer):
    """Full customer detail."""

    portal_login = serializers.SerializerMethodField()
    route_name = serializers.CharField(source="route.name", read_only=True, default=None)

    class Meta:
        model = Customer
        fields = [
            "id",
            "customer_code",
            "name",
            "phone",
            "email",
            "address",
            "location",
            "latitude",
            "longitude",
            "notes",
            "status",
            "route",
            "route_name",
            "portal_login",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "customer_code", "route", "created_at", "updated_at"]

    def get_portal_login(self, obj):
        """{username, is_active} or null — the password is never readable."""
        user = obj.user
        return {"username": user.username, "is_active": user.is_active} if user else None


class CustomerCreateSerializer(serializers.ModelSerializer):
    """Create a customer — customer_code and business are set server-side."""

    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "phone",
            "email",
            "address",
            "location",
            "latitude",
            "longitude",
            "notes",
            "route",
        ]
        read_only_fields = ["id"]

    def validate_route(self, value):
        return _validate_route(self, value)

    def validate_phone(self, value):
        if value:
            business_id = self.context["request"].user.business_id
            if Customer.objects.filter(business_id=business_id, phone=value).exists():
                raise serializers.ValidationError("A customer with this phone already exists.")
        return value


class CustomerUpdateSerializer(serializers.ModelSerializer):
    """Update customer — cannot change customer_code or business."""

    status = serializers.ChoiceField(choices=CUSTOMER_STATUS_CHOICES, required=False)

    class Meta:
        model = Customer
        fields = [
            "name",
            "phone",
            "email",
            "address",
            "location",
            "latitude",
            "longitude",
            "notes",
            "status",
            "route",
        ]

    def validate_route(self, value):
        return _validate_route(self, value)

    def validate_phone(self, value):
        if value:
            business_id = self.instance.business_id
            qs = Customer.objects.filter(business_id=business_id, phone=value).exclude(id=self.instance.id)
            if qs.exists():
                raise serializers.ValidationError("A customer with this phone already exists.")
        return value


class PortalProfileSerializer(serializers.ModelSerializer):
    """What a customer may change about themselves in the portal (model limits apply)."""

    class Meta:
        model = Customer
        fields = ["phone", "email", "address", "location"]

    def validate_phone(self, value):
        if not value:
            raise serializers.ValidationError("Phone number is required.")
        clash = Customer.objects.filter(business_id=self.instance.business_id, phone=value).exclude(
            id=self.instance.id
        )
        if clash.exists():
            raise serializers.ValidationError("Another customer of this mess already uses this phone number.")
        return value


class PortalLoginCreateSerializer(serializers.Serializer):
    """Body for POST /customers/{id}/portal-login/. Omit username → phone; omit password → generated."""

    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(
        max_length=128, required=False, allow_blank=True, trim_whitespace=False, write_only=True
    )


class PortalPasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(
        max_length=128, required=False, allow_blank=True, trim_whitespace=False, write_only=True
    )
