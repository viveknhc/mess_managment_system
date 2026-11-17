"""SUPER_ADMIN: what each business gets (features) and how its workflows run (policies)."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import AuditService
from apps.businesses.models import Business
from apps.customization.serializers import (
    BusinessCustomizationUpdateSerializer,
    business_customization_data,
    catalog_data,
)
from apps.customization.services import FeatureService, PolicyService
from apps.platform.permissions import IsSuperAdmin


class CustomizationCatalogView(APIView):
    """GET /api/v1/platform/customization/catalog/ — every feature and extension point."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        return Response(catalog_data())


class BusinessCustomizationView(APIView):
    """GET/PUT /api/v1/platform/businesses/{id}/customization/."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def _data(self, business):
        inherited, _source = FeatureService.inherited(business.id)
        return business_customization_data(
            FeatureService.resolve(business.id), inherited, PolicyService.selected(business.id)
        )

    def get(self, request, pk):
        return Response(self._data(get_object_or_404(Business, pk=pk)))

    def put(self, request, pk):
        business = get_object_or_404(Business, pk=pk)
        serializer = BusinessCustomizationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        features = serializer.validated_data.get("features", {})
        policies = serializer.validated_data.get("policies", {})

        with transaction.atomic():
            FeatureService.set_overrides(business.id, features)
            for point, choice in policies.items():
                PolicyService.set_policy(business.id, point, choice["policy"], choice["params"])
            changes = [
                f"{k}={'default' if v is None else ('on' if v else 'off')}" for k, v in features.items()
            ]
            changes += [f"{p}={c['policy']}" for p, c in policies.items()]
            if changes:
                AuditService.log(
                    business_id=business.id,
                    user=request.user,
                    action="CUSTOMIZE",
                    entity_type="Business",
                    entity_id=business.id,
                    description="; ".join(changes),
                )
        return Response(self._data(business))
