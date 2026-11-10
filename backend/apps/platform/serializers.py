"""Platform billing serializers."""

from datetime import timedelta

from rest_framework import serializers

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.platform.models import PaymentMethod, SaasPayment, SaasPlan, SaasSubscription
from apps.platform.services import GRACE_DAYS, PlatformService

# ── SaasPlan ──────────────────────────────────────────────────────────────


class SaasPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaasPlan
        fields = [
            "id",
            "name",
            "price_monthly",
            "setup_fee",
            "reactivation_fee",
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
        fields = [
            "id",
            "name",
            "price_monthly",
            "setup_fee",
            "reactivation_fee",
            "max_customers",
            "max_staff",
            "features",
        ]


# ── SaasSubscription ──────────────────────────────────────────────────────


def amount_due_data(sub):
    due = PlatformService.amount_due(sub)
    return {
        "setup_fee": str(due.setup_fee),
        "reactivation_fee": str(due.reactivation_fee),
        "monthly_fee": str(due.monthly_fee),
        "total": str(due.total),
        "due_date": due.due_date.isoformat(),
    }


class SaasSubscriptionSerializer(serializers.ModelSerializer):
    plan_details = SaasPlanPublicSerializer(source="plan", read_only=True, default=None)
    plan_name = serializers.CharField(source="plan.name", read_only=True, default=None)
    plan_price = serializers.DecimalField(
        source="plan.price_monthly", read_only=True, default=None, max_digits=10, decimal_places=2
    )
    business_name = serializers.CharField(source="business.name", read_only=True)
    business_status = serializers.CharField(source="business.status", read_only=True)
    days_remaining = serializers.SerializerMethodField()
    grace_ends = serializers.SerializerMethodField()
    amount_due = serializers.SerializerMethodField()

    class Meta:
        model = SaasSubscription
        fields = [
            "id",
            "business_id",
            "business_name",
            "business_status",
            "plan",
            "plan_name",
            "plan_price",
            "plan_details",
            "status",
            "setup_fee_paid",
            "cancelled_at",
            "trial_end_date",
            "current_period_start",
            "current_period_end",
            "days_remaining",
            "grace_ends",
            "amount_due",
        ]
        read_only_fields = fields

    def get_days_remaining(self, obj):
        from django.utils import timezone

        today = timezone.localdate()
        if obj.status == "TRIAL" and obj.trial_end_date:
            return max(0, (obj.trial_end_date - today).days)
        if obj.current_period_end:
            return max(0, (obj.current_period_end - today).days)
        return None

    def get_grace_ends(self, obj):
        """Last day before suspension when the monthly fee is overdue."""
        if obj.status == "PAST_DUE" and obj.current_period_end:
            return obj.current_period_end + timedelta(days=GRACE_DAYS)
        return None

    def get_amount_due(self, obj):
        return amount_due_data(obj)


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
            "setup_fee",
            "reactivation_fee",
            "status",
            "method",
            "reference",
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
    paid_until = serializers.DateField(
        source="saas_subscription.current_period_end", read_only=True, default=None
    )
    amount_due = serializers.SerializerMethodField()
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
            "paid_until",
            "amount_due",
            "owner_name",
            "owner_email",
            "customer_count",
            "staff_count",
            "created_at",
        ]
        read_only_fields = fields

    def get_amount_due(self, obj):
        sub = getattr(obj, "saas_subscription", None)
        return amount_due_data(sub) if sub else None

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


# ── Platform Admin: onboarding + payments ─────────────────────────────────


class CreateBusinessSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=200)
    phone = serializers.CharField(max_length=20, required=False, default="", allow_blank=True)
    email = serializers.EmailField(required=False, default="", allow_blank=True)
    address = serializers.CharField(required=False, default="", allow_blank=True)
    owner_username = serializers.CharField(max_length=150)
    owner_password = serializers.CharField(min_length=8, write_only=True)
    owner_name = serializers.CharField(max_length=150, required=False, default="", allow_blank=True)
    owner_email = serializers.EmailField(required=False, default="", allow_blank=True)
    owner_phone = serializers.CharField(max_length=20, required=False, default="", allow_blank=True)

    def validate_owner_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value


class RecordPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    method = serializers.ChoiceField(
        choices=[PaymentMethod.UPI, PaymentMethod.CASH, PaymentMethod.BANK_TRANSFER]
    )
    reference = serializers.CharField(max_length=100, required=False, default="", allow_blank=True)
