"""Auth views (Module 1) + Staff management (Module 3)."""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.models import User
from apps.accounts.serializers import (
    CustomTokenObtainPairSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    StaffCreateSerializer,
    StaffListSerializer,
    StaffUpdateSerializer,
    UserSerializer,
)
from apps.accounts.services import InvalidResetLink, PasswordResetService
from common.constants import BUSINESS_STAFF_ROLES, Role
from common.permissions import RoleBasedPermission
from common.viewsets import TenantScopedViewSet


class LoginThrottle(AnonRateThrottle):
    rate = "5/min"


class LoginUsernameThrottle(SimpleRateThrottle):
    """Caps attempts per username across all IPs — stops password guessing spread over
    many addresses. Generous enough that a real user is never blocked by normal use."""

    scope = "login_user"

    def get_cache_key(self, request, view):
        username = str(request.data.get("username", "")).strip().lower()
        if not username:
            return None
        return self.cache_format % {"scope": self.scope, "ident": username}


class PasswordResetThrottle(AnonRateThrottle):
    scope = "password_reset"  # own counter, separate from login attempts
    rate = "5/hour"


class ThrottleUnlessDisabledMixin:
    def get_throttles(self):
        """Skip throttling when rates are disabled (tests)."""
        from django.conf import settings

        if not settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES"):
            return []
        return super().get_throttles()


class LoginView(ThrottleUnlessDisabledMixin, TokenObtainPairView):
    """POST /auth/login/ — returns access, refresh, user + business."""

    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginThrottle, LoginUsernameThrottle]


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


RESET_REQUESTED_MESSAGE = (
    "If an account with that username or email has an email address, we've sent it a reset link."
)


class PasswordResetRequestView(ThrottleUnlessDisabledMixin, APIView):
    """POST /auth/password-reset/ {identifier} — email a reset link.

    Always the same 200 response, so it can't be used to find out which accounts exist.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PasswordResetService.request_reset(serializer.validated_data["identifier"])
        return Response({"detail": RESET_REQUESTED_MESSAGE})


class PasswordResetConfirmView(ThrottleUnlessDisabledMixin, APIView):
    """POST /auth/password-reset/confirm/ {uid, token, new_password} — set the new password."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            PasswordResetService.reset_password(data["uid"], data["token"], data["new_password"])
        except InvalidResetLink:
            raise ValidationError(
                {"detail": "This reset link is invalid or has expired. Ask for a new one."}
            ) from None
        except DjangoValidationError as e:
            raise ValidationError({"new_password": e.messages}) from None
        return Response({"detail": "Password changed. You can now sign in."})


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
    ordering_fields = ["name", "username", "email", "phone", "role", "is_active", "date_joined"]

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
