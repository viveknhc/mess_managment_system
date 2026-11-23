"""Customer API (C-04, C-05)."""

from django.db import models, transaction
from django.http import HttpResponse
from django_filters import rest_framework as django_filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.customers import services
from apps.customers.models import Customer
from apps.customers.serializers import (
    CustomerCreateSerializer,
    CustomerDetailSerializer,
    CustomerListSerializer,
    CustomerUpdateSerializer,
    PortalLoginCreateSerializer,
    PortalPasswordResetSerializer,
)
from apps.customization.permissions import requires_feature
from apps.customization.registry import CUSTOMER_PORTAL
from common.constants import Role, Status
from common.permissions import RoleBasedPermission
from common.viewsets import TenantScopedViewSet


class CustomerFilter(django_filters.FilterSet):
    """Filters for customer list: status, search (name/phone/code/address)."""

    search = django_filters.CharFilter(method="filter_search")
    status = django_filters.CharFilter(field_name="status")
    route = django_filters.UUIDFilter(field_name="route_id")

    class Meta:
        model = Customer
        fields = ["status", "route"]

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

    queryset = Customer.objects.select_related("route").all()
    serializer_class = CustomerListSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filterset_class = CustomerFilter
    ordering_fields = ["customer_code", "name", "phone", "status", "location", "created_at"]

    role_map = {
        "list": [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF],
        "retrieve": [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF],
        "create": [Role.OWNER, Role.MANAGER],
        "update": [Role.OWNER, Role.MANAGER],
        "partial_update": [Role.OWNER, Role.MANAGER],
        "destroy": [Role.OWNER],
        "import_csv": [Role.OWNER, Role.MANAGER],
        "import_template": [Role.OWNER, Role.MANAGER],
        "portal_login": [Role.OWNER, Role.MANAGER],
        "portal_login_reset_password": [Role.OWNER, Role.MANAGER],
        "portal_login_disable": [Role.OWNER, Role.MANAGER],
        "portal_login_enable": [Role.OWNER, Role.MANAGER],
    }

    def get_serializer_class(self):
        if self.action == "create":
            return CustomerCreateSerializer
        if self.action in ("update", "partial_update"):
            return CustomerUpdateSerializer
        if self.action == "retrieve":
            return CustomerDetailSerializer
        return CustomerListSerializer

    @transaction.atomic
    def perform_update(self, serializer):
        new_status = serializer.validated_data.get("status")
        if new_status:
            services.check_can_change_status(serializer.instance, new_status)
        old_route_id = serializer.instance.route_id
        customer = serializer.save()
        services.after_status_change(customer)
        if customer.route_id != old_route_id:
            from apps.deliveries.services import RouteService

            RouteService.sync_customers([customer.id])

    @transaction.atomic
    def perform_destroy(self, instance):
        """Soft-delete: deactivate rather than hard-delete (C-08). Their portal login is disabled too.
        Refused while the customer still has live subscriptions."""
        services.check_can_change_status(instance, Status.INACTIVE)
        instance.status = Status.INACTIVE
        instance.save(update_fields=["status"])
        services.after_status_change(instance)

    @action(
        detail=False,
        methods=["post"],
        url_path="import",
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_csv(self, request):
        """Bulk-create customers from a CSV upload (all-or-nothing, max 100 rows)."""
        upload = request.FILES.get("file")
        if upload is None:
            raise services.CustomerImportError(
                "Please upload a CSV file.", {"file": ["This field is required."]}
            )
        business = request.user.business
        if business is None:
            raise services.CustomerImportError("Your account is not linked to a business.")
        self.get_queryset()  # enforces suspended-business check
        created = services.import_customers(
            business=business,
            raw=upload.read(services.MAX_IMPORT_BYTES + 1),
            serializer_context=self.get_serializer_context(),
        )
        return Response({"created": created}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="import-template")
    def import_template(self, request):
        """Download a CSV template with the header row and one example row."""
        response = HttpResponse(services.build_import_template(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="customers_import_template.csv"'
        return response

    # ── Portal login (owner/manager gives the customer a username + password) ──

    _portal_permissions = [IsAuthenticated, RoleBasedPermission, requires_feature(CUSTOMER_PORTAL)]

    @action(detail=True, methods=["post"], url_path="portal-login", permission_classes=_portal_permissions)
    def portal_login(self, request, pk=None):
        """Create the login. Body: {username?, password?} — username defaults to the phone,
        password is generated when blank. The response carries the password once."""
        customer = self.get_object()
        body = PortalLoginCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        result = services.create_portal_login(customer, **body.validated_data)
        return Response(result, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["post"],
        url_path="portal-login/reset-password",
        permission_classes=_portal_permissions,
    )
    def portal_login_reset_password(self, request, pk=None):
        """Body: {password?} — generated when blank. Signs the customer out everywhere."""
        customer = self.get_object()
        body = PortalPasswordResetSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        return Response(services.reset_portal_password(customer, **body.validated_data))

    @action(
        detail=True, methods=["post"], url_path="portal-login/disable", permission_classes=_portal_permissions
    )
    def portal_login_disable(self, request, pk=None):
        return Response(services.set_portal_login_active(self.get_object(), False))

    @action(
        detail=True, methods=["post"], url_path="portal-login/enable", permission_classes=_portal_permissions
    )
    def portal_login_enable(self, request, pk=None):
        customer = self.get_object()
        if customer.status != Status.ACTIVE:
            raise ValidationError(
                {
                    "detail": f"{customer.name} is {customer.get_status_display().lower()}. Make them active first."
                }
            )
        return Response(services.set_portal_login_active(customer, True))
