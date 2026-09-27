"""Customer API (C-04, C-05)."""

from django.db import models
from django_filters import rest_framework as django_filters
from rest_framework.permissions import IsAuthenticated

from apps.customers.models import Customer
from apps.customers.serializers import (
    CustomerCreateSerializer,
    CustomerDetailSerializer,
    CustomerListSerializer,
    CustomerUpdateSerializer,
)
from common.constants import Role
from common.permissions import RoleBasedPermission
from common.viewsets import TenantScopedViewSet


class CustomerFilter(django_filters.FilterSet):
    """Filters for customer list: status, search (name/phone/code/address)."""

    search = django_filters.CharFilter(method="filter_search")
    status = django_filters.CharFilter(field_name="status")

    class Meta:
        model = Customer
        fields = ["status"]

    def filter_search(self, queryset, _name, value):
        if not value:
            return queryset
        return queryset.filter(
            models.Q(name__icontains=value)
            | models.Q(phone__icontains=value)
            | models.Q(customer_code__icontains=value)
            | models.Q(address__icontains=value)
        )


class CustomerViewSet(TenantScopedViewSet):
    """CRUD for customers.

    - OWNER / MANAGER can create, update, and view customers.
    - DELIVERY_STAFF / KITCHEN_STAFF can view (read-only).
    - Soft-delete: sets status to INACTIVE rather than hard delete.
    """

    queryset = Customer.objects.all()
    serializer_class = CustomerListSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filterset_class = CustomerFilter

    role_map = {
        "list": [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF],
        "retrieve": [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF],
        "create": [Role.OWNER, Role.MANAGER],
        "update": [Role.OWNER, Role.MANAGER],
        "partial_update": [Role.OWNER, Role.MANAGER],
        "destroy": [Role.OWNER],
    }

    def get_serializer_class(self):
        if self.action == "create":
            return CustomerCreateSerializer
        if self.action in ("update", "partial_update"):
            return CustomerUpdateSerializer
        if self.action == "retrieve":
            return CustomerDetailSerializer
        return CustomerListSerializer

    def perform_destroy(self, instance):
        """Soft-delete: deactivate rather than hard-delete (C-08)."""
        instance.status = "INACTIVE"
        instance.save(update_fields=["status"])
