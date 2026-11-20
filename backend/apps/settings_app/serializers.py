"""BusinessSettings serializer (ST-02)."""

from rest_framework import serializers

from apps.customization.registry import ONLINE_PAYMENTS, SKIP
from apps.customization.services import FeatureService, PolicyService
from apps.settings_app.models import BusinessSettings


class BusinessSettingsSerializer(serializers.ModelSerializer):
    # Write-only: the secret is stored encrypted and never sent back. Blank = keep the saved one.
    razorpay_key_secret = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=128, trim_whitespace=True
    )
    razorpay_configured = serializers.BooleanField(read_only=True)
    # Workflow policies are chosen by SUPER_ADMIN (customization); owners see them read-only.
    skip_policy = serializers.SerializerMethodField()

    class Meta:
        model = BusinessSettings
        fields = [
            "id",
            "min_pause_days",
            "max_pause_days",
            "skip_policy",
            "delivery_start_time",
            "delivery_end_time",
            "notify_on_payment",
            "notify_on_expiring",
            "notify_on_delivery",
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
        return super().update(instance, validated_data)
