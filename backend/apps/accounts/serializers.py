"""Auth + staff serializers."""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import User
from common.constants import BUSINESS_STAFF_ROLES, Role


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Extend JWT login to include user profile and business in the response."""

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data["user"] = UserSerializer(user).data
        return data


class UserSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source="business.name", read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "name",
            "email",
            "phone",
            "role",
            "is_active",
            "business_id",
            "business_name",
        ]
        read_only_fields = fields


# ── Staff management serializers (U-01) ──────────────────────────────────

STAFF_ROLE_CHOICES = [(r, r) for r in BUSINESS_STAFF_ROLES]


class StaffListSerializer(serializers.ModelSerializer):
    """Read-only serializer for staff list/detail."""

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "name",
            "email",
            "phone",
            "role",
            "is_active",
            "date_joined",
        ]
        read_only_fields = fields


class StaffCreateSerializer(serializers.ModelSerializer):
    """Create a new staff member. Password required, business set server-side."""

    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=STAFF_ROLE_CHOICES)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "password",
            "name",
            "email",
            "phone",
            "role",
        ]
        read_only_fields = ["id"]

    def validate_role(self, value):
        # Cannot create SUPER_ADMIN or CUSTOMER via staff endpoint
        if value not in BUSINESS_STAFF_ROLES:
            raise serializers.ValidationError(f"Invalid staff role: {value}")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class StaffUpdateSerializer(serializers.ModelSerializer):
    """Update staff — name, email, phone, role, is_active. No password/username change."""

    role = serializers.ChoiceField(choices=STAFF_ROLE_CHOICES)

    class Meta:
        model = User
        fields = ["name", "email", "phone", "role", "is_active"]

    def validate_role(self, value):
        if value not in BUSINESS_STAFF_ROLES:
            raise serializers.ValidationError(f"Invalid staff role: {value}")
        # Prevent demoting the last owner
        instance = self.instance
        if (
            instance
            and instance.role == Role.OWNER
            and value != Role.OWNER
            and not User.objects.filter(business_id=instance.business_id, role=Role.OWNER, is_active=True)
            .exclude(id=instance.id)
            .exists()
        ):
            raise serializers.ValidationError("Cannot remove the last active owner.")
        return value
