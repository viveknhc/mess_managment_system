"""Tenant-scoped viewset base (arch. §5).

Every business-owned ViewSet inherits this. Never write `Model.objects.all()`
in an app viewset — tenant filtering and business force-set happen here.
"""

from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from common.constants import Role, Status
from common.permissions import IsSameBusiness


class TenantScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSameBusiness]

    def get_queryset(self):
        assert self.queryset is not None, "TenantScopedViewSet requires .queryset"
        user = self.request.user
        # SUPER_ADMIN bypasses suspension check
        if getattr(user, "role", None) != Role.SUPER_ADMIN:
            business = getattr(user, "business", None)
            if business and business.status == Status.SUSPENDED:
                raise PermissionDenied("Your business account is suspended. Please contact support.")
        return self.queryset.filter(business_id=user.business_id)

    def perform_create(self, serializer):
        business = self.request.user.business
        # Quota check — raises 402 if plan limit reached
        if getattr(self.request.user, "role", None) != Role.SUPER_ADMIN and business:
            from apps.platform.middleware import check_quota

            model_class = self.queryset.model
            check_quota(business, model_class)
        serializer.save(business_id=self.request.user.business_id)  # client value ignored
