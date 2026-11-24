"""BusinessSettings serializer (ST-02)."""

from django.db import transaction
from rest_framework import serializers

from apps.customization.registry import ONLINE_PAYMENTS, SKIP
from apps.customization.services import FeatureService, PolicyService
from apps.settings_app.models import BusinessSettings

WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _day_names(days):
    return ", ".join(WEEKDAY_NAMES[d] for d in days) or "none"


class BusinessSettingsSerializer(serializers.ModelSerializer):
    # Write-only: the secret is stored encrypted and never sent back. Blank = keep the saved one.
    razorpay_key_secret = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=128, trim_whitespace=True
    )
    razorpay_configured = serializers.BooleanField(read_only=True)
    # Days the kitchen is closed every week: 0=Monday … 6=Sunday.
    weekly_off_days = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6), required=False, max_length=7
    )
    # Workflow policies are chosen by SUPER_ADMIN (customization); owners see them read-only.
    skip_policy = serializers.SerializerMethodField()

    class Meta:
        model = BusinessSettings
        fields = [
            "id",
            "min_pause_days",
            "max_pause_days",
            "skip_policy",
            "weekly_off_days",
            "delivery_start_time",
            "delivery_end_time",
            "notify_on_payment",
            "notify_on_expiring",
            "notify_on_delivery",
            "upi_id",
            "online_payments_enabled",
            "razorpay_key_id",
            "razorpay_key_secret",
            "razorpay_configured",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def get_skip_policy(self, obj):
        policy = PolicyService.get(obj.business_id, SKIP)
        return {"key": policy.key, "label": policy.label, "description": policy.description}

    def validate_online_payments_enabled(self, value):
        """Switching on needs the feature. An already-on flag may be re-sent (whole-form saves) —
        it does nothing while the feature is off: OnlinePaymentService checks the feature too."""
        inst = self.instance
        turning_on = value and not (inst and inst.online_payments_enabled)
        if turning_on and inst and not FeatureService.has(inst.business_id, ONLINE_PAYMENTS):
            raise serializers.ValidationError("Online payments are not included in your MessDeck plan.")
        return value

    def validate_upi_id(self, value):
        from apps.payments.services import UPI_ID_RE

        value = value.strip().lower()
        if value and not UPI_ID_RE.match(value):
            raise serializers.ValidationError("Enter a UPI ID like yourname@okicici.")
        inst = self.instance
        if (
            value
            and inst
            and value != inst.upi_id
            and not FeatureService.has(inst.business_id, ONLINE_PAYMENTS)
        ):
            raise serializers.ValidationError("Online payments are not included in your MessDeck plan.")
        return value

    def validate_weekly_off_days(self, value):
        days = sorted(set(value))
        if len(days) == 7:
            raise serializers.ValidationError("The kitchen must be open at least one day a week.")
        return days

    def validate_razorpay_key_id(self, value):
        value = value.strip()
        if value and not value.startswith(("rzp_test_", "rzp_live_")):
            raise serializers.ValidationError("Key ID starts with rzp_test_ or rzp_live_.")
        return value

    def validate(self, attrs):
        inst = self.instance
        min_days = attrs.get("min_pause_days", inst.min_pause_days if inst else 1)
        max_days = attrs.get("max_pause_days", inst.max_pause_days if inst else 7)
        if min_days > max_days:
            raise serializers.ValidationError(
                {"min_pause_days": "Minimum pause can't be longer than the maximum pause."}
            )
        key_id = attrs.get("razorpay_key_id", inst.razorpay_key_id if inst else "")
        secret = attrs.get("razorpay_key_secret", "")
        if "razorpay_key_id" in attrs and not key_id:
            attrs["razorpay_key_secret"] = ""  # clearing the key ID removes the secret too
            attrs["online_payments_enabled"] = False
        elif attrs.get("online_payments_enabled", inst.online_payments_enabled if inst else False):
            has_secret = bool(secret) or bool(inst and inst.razorpay_configured)
            if not (key_id and has_secret):
                raise serializers.ValidationError(
                    {"online_payments_enabled": "Add your Razorpay Key ID and Key Secret first."}
                )
        return attrs

    def update(self, instance, validated_data):
        clear = "razorpay_key_id" in validated_data and not validated_data["razorpay_key_id"]
        secret = validated_data.pop("razorpay_key_secret", "")
        if secret or clear:
            instance.set_razorpay_secret(secret)
        old_off_days = sorted(instance.weekly_off_days or [])
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            new_off_days = sorted(instance.weekly_off_days or [])
            if new_off_days != old_off_days:
                from apps.audit.services import AuditService
                from apps.subscriptions.services import SubscriptionService

                moved = SubscriptionService.apply_kitchen_calendar(instance.business_id)
                request = self.context.get("request")
                AuditService.log(
                    business_id=instance.business_id,
                    user=request.user if request else None,
                    action="UPDATE",
                    entity_type="BusinessSettings",
                    entity_id=instance.id,
                    description=(
                        f"Kitchen closed on: {_day_names(new_off_days)} (was {_day_names(old_off_days)}); "
                        f"{moved} subscription(s) rescheduled"
                    ),
                )
        return instance
