"""Settings API (ST-02). Owner-only read/write."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.settings_app.models import BusinessSettings
from apps.settings_app.serializers import BusinessSettingsSerializer
from common.constants import Role


class BusinessSettingsView(APIView):
    """GET/PUT /api/v1/settings/ — business configuration."""

    permission_classes = [IsAuthenticated]

    def get_settings(self, request):
        settings, _ = BusinessSettings.objects.get_or_create(business_id=request.user.business_id)
        return settings

    def get(self, request):
        role = getattr(request.user, "role", None)
        if role not in (Role.OWNER, Role.MANAGER, Role.SUPER_ADMIN):
            return Response(
                {"error": {"code": "PERMISSION_DENIED", "message": "Settings access denied.", "fields": {}}},
                status=403,
            )
        settings = self.get_settings(request)
        return Response(BusinessSettingsSerializer(settings).data)

    def put(self, request):
        role = getattr(request.user, "role", None)
        if role != Role.OWNER:
            return Response(
                {
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": "Only owner can update settings.",
                        "fields": {},
                    }
                },
                status=403,
            )
        settings = self.get_settings(request)
        serializer = BusinessSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
