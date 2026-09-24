"""Tenant-scoped viewset base (arch. §5).

Every business-owned ViewSet inherits this. Never write `Model.objects.all()`
in an app viewset — tenant filtering and business force-set happen here.
"""

from rest_framework import viewsets

from common.permissions import IsSameBusiness


class TenantScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSameBusiness]

    def get_queryset(self):
        assert self.queryset is not None, "TenantScopedViewSet requires .queryset"
        return self.queryset.filter(business_id=self.request.user.business_id)

    def perform_create(self, serializer):
        serializer.save(business_id=self.request.user.business_id)  # client value ignored
