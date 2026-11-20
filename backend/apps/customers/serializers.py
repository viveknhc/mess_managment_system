"""Customer serializers (C-03)."""

from rest_framework import serializers

from apps.customers.models import Customer
from common.constants import Status

CUSTOMER_STATUS_CHOICES = [
    (Status.ACTIVE, "Active"),
    (Status.INACTIVE, "Inactive"),
    (Status.BLOCKED, "Blocked"),
]


class CustomerListSerializer(serializers.ModelSerializer):
    """Read-only serializer for customer list."""

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
            "created_at",
        ]
        read_only_fields = fields


class CustomerDetailSerializer(serializers.ModelSerializer):
    """Full customer detail."""

    portal_login = serializers.SerializerMethodField()

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
            "portal_login",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "customer_code", "created_at", "updated_at"]

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
        ]
        read_only_fields = ["id"]

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
        ]

    def validate_phone(self, value):
        if value:
            business_id = self.instance.business_id
            qs = Customer.objects.filter(business_id=business_id, phone=value).exclude(id=self.instance.id)
            if qs.exists():
                raise serializers.ValidationError("A customer with this phone already exists.")
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
