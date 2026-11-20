"""Auth + staff serializers."""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import User
from apps.customization.services import FeatureService
from common.authentication import saas_status, trial_ends_at
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
    business_status = serializers.CharField(source="business.status", read_only=True, default=None)
    saas_status = serializers.SerializerMethodField()
    trial_ends_at = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()

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
            "business_status",
            "saas_status",
            "trial_ends_at",
            "features",
        ]
        read_only_fields = fields

    def get_saas_status(self, obj):
        """MessDeck billing status — PENDING means the app is locked until the first payment."""
        return saas_status(obj.business)

    def get_trial_ends_at(self, obj):
        """End of the free trial (TRIAL only) — the owner sees a countdown; past it the app locks."""
        ends = trial_ends_at(obj.business)
        return ends.isoformat() if ends else None

    def get_features(self, obj):
        """Feature keys the user's business has — the frontend hides what's missing."""
        return sorted(FeatureService.enabled(obj.business_id))


class PasswordResetRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254, help_text="Username or email")


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=64)
    token = serializers.CharField(max_length=128)
    new_password = serializers.CharField(max_length=128, trim_whitespace=False)


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
