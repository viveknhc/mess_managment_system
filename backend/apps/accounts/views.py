"""Auth views (Module 1)."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.serializers import CustomTokenObtainPairSerializer, UserSerializer


class LoginThrottle(AnonRateThrottle):
    rate = "5/min"


class LoginView(TokenObtainPairView):
    """POST /auth/login/ — returns access, refresh, user + business."""

    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]

    def get_throttles(self):
        """Skip throttling when rates are disabled (tests)."""
        from django.conf import settings

        if not settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES"):
            return []
        return super().get_throttles()


class RefreshView(TokenRefreshView):
    """POST /auth/refresh/ — standard simplejwt refresh with rotation."""

    pass


class LogoutView(APIView):
    """POST /auth/logout/ — blacklist the refresh token."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "Refresh token required.", "fields": {}}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "Invalid or expired token.", "fields": {}}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Logged out."}, status=status.HTTP_200_OK)


class MeView(APIView):
    """GET /auth/me/ — return current user profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
