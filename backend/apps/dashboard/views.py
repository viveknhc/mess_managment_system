"""Dashboard API (DB-01)."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dashboard.selectors import get_dashboard_data
from common.constants import Role


class DashboardView(APIView):
    """GET /api/v1/dashboard/ — aggregated KPIs."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = getattr(request.user, "role", None)
        if role not in (Role.OWNER, Role.MANAGER, Role.SUPER_ADMIN):
            return Response(
                {"error": {"code": "PERMISSION_DENIED", "message": "Dashboard access denied.", "fields": {}}},
                status=403,
            )
        data = get_dashboard_data(request.user.business_id)
        return Response(data)
