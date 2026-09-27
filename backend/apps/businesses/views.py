"""Business profile API (Module 2).

Not a typical TenantScopedViewSet — Business IS the tenant. Users see
only their own business. Only OWNER can update.
"""

from rest_framework.permissions import IsAuthenticated

from apps.businesses.models import Business
from apps.businesses.serializers import BusinessSerializer, BusinessUpdateSerializer
from common.constants import Role
from common.permissions import RoleBasedPermission
from common.viewsets import TenantScopedViewSet


class BusinessViewSet(TenantScopedViewSet):
    """Users see and manage only their own business.

    - All authenticated users can read their business profile.
    - Only OWNER can update.
    - Create/delete disabled (business created via bootstrap command).
    """

    serializer_class = BusinessSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    http_method_names = ["get", "put", "patch", "head", "options"]

    role_map = {
        "list": [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF, Role.CUSTOMER],
        "retrieve": [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF, Role.CUSTOMER],
        "update": [Role.OWNER],
        "partial_update": [Role.OWNER],
    }

    def get_queryset(self):
        return Business.objects.filter(id=self.request.user.business_id)

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return BusinessUpdateSerializer
        return BusinessSerializer
