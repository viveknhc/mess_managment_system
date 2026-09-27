"""Plan serializers (P-02)."""

from rest_framework import serializers

from apps.plans.models import Plan


class PlanListSerializer(serializers.ModelSerializer):
    """Read-only for list view. Includes meal name."""

    meal_name = serializers.CharField(source="meal.name", read_only=True)

    class Meta:
        model = Plan
        fields = [
            "id",
            "name",
            "description",
            "meal",
            "meal_name",
            "duration_days",
            "total_meals",
            "price",
            "skip_allowed",
            "pause_allowed",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields


class PlanCreateSerializer(serializers.ModelSerializer):
    """Create/update a plan. Validates total_meals vs duration and meal ownership."""

    class Meta:
        model = Plan
        fields = [
            "id",
            "name",
            "description",
            "meal",
            "duration_days",
            "total_meals",
            "price",
            "skip_allowed",
            "pause_allowed",
        ]
        read_only_fields = ["id"]

    def validate_name(self, value):
        business_id = self.context["request"].user.business_id
        qs = Plan.objects.filter(business_id=business_id, name__iexact=value)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError("A plan with this name already exists.")
        return value

    def validate_meal(self, value):
        """Ensure the meal belongs to the same business."""
        business_id = self.context["request"].user.business_id
        if value.business_id != business_id:
            raise serializers.ValidationError("Meal not found.")
        if not value.is_active:
            raise serializers.ValidationError("Cannot use an inactive meal.")
        return value

    def validate(self, data):
        duration = data.get("duration_days") or (self.instance and self.instance.duration_days)
        total = data.get("total_meals") or (self.instance and self.instance.total_meals)
        if duration and total and total > duration:
            raise serializers.ValidationError({"total_meals": "Total meals cannot exceed duration days."})
        price = data.get("price")
        if price is not None and price < 0:
            raise serializers.ValidationError({"price": "Price must be >= 0."})
        return data


class PlanUpdateSerializer(PlanCreateSerializer):
    """Update — same validations, adds is_active toggle."""

    class Meta(PlanCreateSerializer.Meta):
        fields = PlanCreateSerializer.Meta.fields + ["is_active"]
