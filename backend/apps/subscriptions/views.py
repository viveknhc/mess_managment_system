"""Subscription API (S-05, S-06, S-07)."""

from django.db import models
from django_filters import rest_framework as django_filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.subscriptions.models import Subscription
from apps.subscriptions.serializers import (
    SubscriptionCreateSerializer,
    SubscriptionDetailSerializer,
    SubscriptionListSerializer,
)
from apps.subscriptions.services import SubscriptionService
from common.constants import Role
from common.permissions import RoleBasedPermission
from common.viewsets import TenantScopedViewSet


class SubscriptionFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status")
    customer = django_filters.UUIDFilter(field_name="customer_id")
    plan = django_filters.UUIDFilter(field_name="plan_id")
    expiring = django_filters.BooleanFilter(method="filter_expiring")

    class Meta:
        model = Subscription
        fields = ["status", "customer", "plan"]

    def filter_expiring(self, queryset, _name, value):
        import datetime
        from datetime import timedelta

        if value:
            today = datetime.date.today()
            return queryset.filter(
                models.Q(status="ACTIVE")
                & models.Q(end_date__gte=today)
                & models.Q(end_date__lte=today + timedelta(days=3))
            )
        return queryset


class SubscriptionViewSet(TenantScopedViewSet):
    """CRUD + actions for subscriptions.

    - OWNER / MANAGER can create, pause, resume, cancel, renew.
    - All staff can view.
    - No update/delete — state changes via actions only.
    """

    queryset = Subscription.objects.select_related("customer", "plan").all()
    serializer_class = SubscriptionListSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filterset_class = SubscriptionFilter
    http_method_names = ["get", "post", "head", "options"]

    role_map = {
        "list": [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF],
        "retrieve": [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF],
        "create": [Role.OWNER, Role.MANAGER],
        "pause": [Role.OWNER, Role.MANAGER],
        "resume": [Role.OWNER, Role.MANAGER],
        "cancel": [Role.OWNER, Role.MANAGER],
        "renew": [Role.OWNER, Role.MANAGER],
    }

    def get_serializer_class(self):
        if self.action == "create":
            return SubscriptionCreateSerializer
        if self.action == "retrieve":
            return SubscriptionDetailSerializer
        return SubscriptionListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sub = SubscriptionService.create_subscription(
            business_id=request.user.business_id,
            customer=serializer.validated_data["customer"],
            plan=serializer.validated_data["plan"],
            start_date=serializer.validated_data["start_date"],
        )
        return Response(
            SubscriptionDetailSerializer(sub).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        sub = self.get_object()
        try:
            sub = SubscriptionService.pause(sub)
        except ValueError as e:
            return Response(
                {"error": {"code": "INVALID_TRANSITION", "message": str(e), "fields": {}}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(SubscriptionDetailSerializer(sub).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        sub = self.get_object()
        try:
            sub = SubscriptionService.resume(sub)
        except ValueError as e:
            return Response(
                {"error": {"code": "INVALID_TRANSITION", "message": str(e), "fields": {}}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(SubscriptionDetailSerializer(sub).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        sub = self.get_object()
        try:
            sub = SubscriptionService.cancel(sub)
        except ValueError as e:
            return Response(
                {"error": {"code": "INVALID_TRANSITION", "message": str(e), "fields": {}}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(SubscriptionDetailSerializer(sub).data)

    @action(detail=True, methods=["post"])
    def renew(self, request, pk=None):
        sub = self.get_object()
        try:
            new_sub = SubscriptionService.renew(sub)
        except ValueError as e:
            return Response(
                {"error": {"code": "INVALID_TRANSITION", "message": str(e), "fields": {}}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            SubscriptionDetailSerializer(new_sub).data,
            status=status.HTTP_201_CREATED,
        )
