"""Platform billing serializers."""

from rest_framework import serializers

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.platform.models import SaasPayment, SaasPlan, SaasSubscription

# ── SaasPlan ──────────────────────────────────────────────────────────────


class SaasPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaasPlan
        fields = [
            "id",
            "name",
            "price_monthly",
            "max_customers",
            "max_staff",
            "features",
            "razorpay_plan_id",
            "is_active",
        ]


class SaasPlanPublicSerializer(serializers.ModelSerializer):
    """Public-facing plan info (no Razorpay IDs)."""

    class Meta:
        model = SaasPlan
        fields = ["id", "name", "price_monthly", "max_customers", "max_staff", "features"]


# ── SaasSubscription ──────────────────────────────────────────────────────


class SaasSubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True, default=None)
    plan_price = serializers.DecimalField(
        source="plan.price_monthly", read_only=True, default=None, max_digits=10, decimal_places=2
    )
    business_name = serializers.CharField(source="business.name", read_only=True)
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = SaasSubscription
        fields = [
            "id",
            "business_id",
            "business_name",
            "plan",
            "plan_name",
            "plan_price",
            "status",
            "trial_end_date",
            "current_period_start",
            "current_period_end",
            "days_remaining",
        ]
        read_only_fields = fields

    def get_days_remaining(self, obj):
        from django.utils import timezone

        today = timezone.now().date()
        if obj.status == "TRIAL" and obj.trial_end_date:
            return max(0, (obj.trial_end_date - today).days)
        if obj.current_period_end:
            return max(0, (obj.current_period_end - today).days)
        return None


# ── SaasPayment ───────────────────────────────────────────────────────────


class SaasPaymentSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source="business.name", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True, default=None)

    class Meta:
        model = SaasPayment
        fields = [
            "id",
            "business_id",
            "business_name",
            "plan_name",
            "amount",
            "status",
            "razorpay_payment_id",
            "period_start",
            "period_end",
            "failure_reason",
            "created_at",
        ]
        read_only_fields = fields


# ── Platform Admin: Business list ─────────────────────────────────────────


class PlatformBusinessSerializer(serializers.ModelSerializer):
    saas_status = serializers.CharField(source="saas_subscription.status", read_only=True, default=None)
    plan_name = serializers.CharField(source="saas_subscription.plan.name", read_only=True, default=None)
    trial_end_date = serializers.DateField(
        source="saas_subscription.trial_end_date", read_only=True, default=None
    )
    owner_name = serializers.SerializerMethodField()
    owner_email = serializers.SerializerMethodField()
    customer_count = serializers.SerializerMethodField()
    staff_count = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            "id",
            "name",
            "phone",
            "email",
            "status",
            "saas_status",
            "plan_name",
            "trial_end_date",
            "owner_name",
            "owner_email",
            "customer_count",
            "staff_count",
            "created_at",
        ]
        read_only_fields = fields

    def get_owner_name(self, obj):
        owner = obj.users.filter(role="OWNER").first()
        return owner.name if owner else None

    def get_owner_email(self, obj):
        owner = obj.users.filter(role="OWNER").first()
        return owner.email if owner else None

    def get_customer_count(self, obj):
        if hasattr(obj, "customers"):
            return obj.customers.count()
        return 0

    def get_staff_count(self, obj):
        return obj.users.exclude(role="CUSTOMER").count()


# ── Signup ────────────────────────────────────────────────────────────────


class SignupSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=200)
    owner_username = serializers.CharField(max_length=150)
    owner_password = serializers.CharField(min_length=8, write_only=True)
    owner_name = serializers.CharField(max_length=150, required=False, default="")
    owner_email = serializers.EmailField(required=False, default="")
    owner_phone = serializers.CharField(max_length=20, required=False, default="")

    def validate_owner_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value


# ── Billing Checkout ──────────────────────────────────────────────────────


class CheckoutSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()

    def validate_plan_id(self, value):
        if not SaasPlan.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Invalid or inactive plan.")
        return value
