"""Auth views (Module 1) + Staff management (Module 3)."""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.models import User
from apps.accounts.serializers import (
    CustomTokenObtainPairSerializer,
    StaffCreateSerializer,
    StaffListSerializer,
    StaffUpdateSerializer,
    UserSerializer,
)
from common.constants import BUSINESS_STAFF_ROLES, Role
from common.permissions import RoleBasedPermission
from common.viewsets import TenantScopedViewSet


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


# ── Staff management (Module 3) ─────────────────────────────────────────


class StaffViewSet(TenantScopedViewSet):
    """CRUD for business staff members.

    - OWNER can list/create/update/activate/deactivate staff.
    - MANAGER can list/retrieve staff (read-only).
    - Other roles cannot access staff management.
    - Business isolation enforced via TenantScopedViewSet.
    """

    queryset = User.objects.all()
    serializer_class = StaffListSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]

    role_map = {
        "list": [Role.OWNER, Role.MANAGER],
        "retrieve": [Role.OWNER, Role.MANAGER],
        "create": [Role.OWNER],
        "update": [Role.OWNER],
        "partial_update": [Role.OWNER],
        "destroy": [Role.OWNER],
        "activate": [Role.OWNER],
        "deactivate": [Role.OWNER],
    }

    def get_queryset(self):
        return (
            User.objects.filter(business_id=self.request.user.business_id, role__in=BUSINESS_STAFF_ROLES)
            .exclude(id=self.request.user.id)
            .order_by("name")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return StaffCreateSerializer
        if self.action in ("update", "partial_update"):
            return StaffUpdateSerializer
        return StaffListSerializer

    def perform_create(self, serializer):
        serializer.save(business_id=self.request.user.business_id)

    def perform_destroy(self, instance):
        """Soft-delete: deactivate rather than hard-delete."""
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        staff = self.get_object()
        staff.is_active = True
        staff.save(update_fields=["is_active"])
        return Response(StaffListSerializer(staff).data)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        staff = self.get_object()
        if staff.role == Role.OWNER:
            # Prevent deactivating the last owner
            other_owners = User.objects.filter(
                business_id=staff.business_id, role=Role.OWNER, is_active=True
            ).exclude(id=staff.id)
            if not other_owners.exists():
                return Response(
                    {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Cannot deactivate the last active owner.",
                            "fields": {},
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        staff.is_active = False
        staff.save(update_fields=["is_active"])
        return Response(StaffListSerializer(staff).data)
