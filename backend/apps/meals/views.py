"""Meal API (M-02)."""

from django_filters import rest_framework as django_filters
from rest_framework.permissions import IsAuthenticated

from apps.meals.models import Meal
from apps.meals.serializers import MealSerializer
from common.constants import Role
from common.permissions import RoleBasedPermission
from common.viewsets import TenantScopedViewSet


class MealFilter(django_filters.FilterSet):
    is_active = django_filters.BooleanFilter(field_name="is_active")

    class Meta:
        model = Meal
        fields = ["is_active"]


class MealViewSet(TenantScopedViewSet):
    """CRUD for meal types.

    - OWNER / MANAGER can create, update, toggle active.
    - All staff roles can view.
    """

    queryset = Meal.objects.all()
    serializer_class = MealSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filterset_class = MealFilter

    role_map = {
        "list": [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF],
        "retrieve": [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF],
        "create": [Role.OWNER, Role.MANAGER],
        "update": [Role.OWNER, Role.MANAGER],
        "partial_update": [Role.OWNER, Role.MANAGER],
        "destroy": [Role.OWNER],
    }

    def perform_destroy(self, instance):
        """Soft-delete: deactivate rather than hard-delete."""
        instance.is_active = False
        instance.save(update_fields=["is_active"])
