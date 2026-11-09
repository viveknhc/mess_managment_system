"""BusinessSettings serializer (ST-02)."""

from rest_framework import serializers

from apps.settings_app.models import BusinessSettings


class BusinessSettingsSerializer(serializers.ModelSerializer):
    # Write-only: the secret is stored encrypted and never sent back. Blank = keep the saved one.
    razorpay_key_secret = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=128, trim_whitespace=True
    )
    razorpay_configured = serializers.BooleanField(read_only=True)

    class Meta:
        model = BusinessSettings
        fields = [
            "id",
            "max_skip_days",
            "min_pause_days",
            "max_pause_days",
            "skip_rule",
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

    def validate_razorpay_key_id(self, value):
        value = value.strip()
        if value and not value.startswith(("rzp_test_", "rzp_live_")):
            raise serializers.ValidationError("Key ID starts with rzp_test_ or rzp_live_.")
        return value

    def validate(self, attrs):
        inst = self.instance
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
