"""BusinessSettings serializer (ST-02)."""

from rest_framework import serializers

from apps.settings_app.models import BusinessSettings


class BusinessSettingsSerializer(serializers.ModelSerializer):
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
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]
