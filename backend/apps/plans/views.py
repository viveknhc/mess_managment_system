"""Plan API (P-03)."""

from django_filters import rest_framework as django_filters
from rest_framework.permissions import IsAuthenticated

from apps.plans.models import Plan
from apps.plans.serializers import PlanCreateSerializer, PlanListSerializer, PlanUpdateSerializer
from common.constants import Role
from common.permissions import RoleBasedPermission
from common.viewsets import TenantScopedViewSet


class PlanFilter(django_filters.FilterSet):
    is_active = django_filters.BooleanFilter(field_name="is_active")
    meal = django_filters.UUIDFilter(field_name="meal_id")

    class Meta:
        model = Plan
        fields = ["is_active", "meal"]


class PlanViewSet(TenantScopedViewSet):
    """CRUD for subscription plans.

    - OWNER / MANAGER can create, update, toggle active.
    - All staff + customer roles can view active plans.
    - Soft-delete: deactivate (existing subscriptions stay valid).
    """

    queryset = Plan.objects.select_related("meal").all()
    serializer_class = PlanListSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filterset_class = PlanFilter

    role_map = {
        "list": [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF, Role.CUSTOMER],
        "retrieve": [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF, Role.CUSTOMER],
        "create": [Role.OWNER, Role.MANAGER],
        "update": [Role.OWNER, Role.MANAGER],
        "partial_update": [Role.OWNER, Role.MANAGER],
        "destroy": [Role.OWNER],
    }

    def get_serializer_class(self):
        if self.action == "create":
            return PlanCreateSerializer
        if self.action in ("update", "partial_update"):
            return PlanUpdateSerializer
        return PlanListSerializer

    def perform_destroy(self, instance):
        """Soft-delete: deactivate rather than hard-delete."""
        instance.is_active = False
        instance.save(update_fields=["is_active"])
