"""Auth serializers — custom token pair returns user + business context."""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Extend JWT login to include user profile and business in the response."""

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data["user"] = UserSerializer(user).data
        return data


class UserSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source="business.name", read_only=True, default=None)

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
        ]
        read_only_fields = fields
