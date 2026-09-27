"""Business serializers (Module 2)."""

from rest_framework import serializers

from apps.businesses.models import Business


class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = [
            "id",
            "name",
            "phone",
            "email",
            "address",
            "logo",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class BusinessUpdateSerializer(serializers.ModelSerializer):
    """Owner-only update — cannot change status or id."""

    class Meta:
        model = Business
        fields = ["name", "phone", "email", "address", "logo"]
