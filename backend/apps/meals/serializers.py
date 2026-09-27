"""Meal serializers."""

from rest_framework import serializers

from apps.meals.models import Meal


class MealSerializer(serializers.ModelSerializer):
    """Read/write serializer for meals. business_id is read-only."""

    class Meta:
        model = Meal
        fields = [
            "id",
            "name",
            "description",
            "price",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        business_id = self.context["request"].user.business_id
        qs = Meal.objects.filter(business_id=business_id, name__iexact=value)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError("A meal with this name already exists.")
        return value
