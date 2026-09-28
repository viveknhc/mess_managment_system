"""Payment API (PAY-05, PAY-06)."""

from django_filters import rest_framework as django_filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.payments.models import Payment
from apps.payments.serializers import PaymentCreateSerializer, PaymentListSerializer
from apps.payments.services import PaymentSelector, PaymentService
from common.constants import Role
from common.permissions import RoleBasedPermission
from common.viewsets import TenantScopedViewSet


class PaymentFilter(django_filters.FilterSet):
    subscription = django_filters.UUIDFilter(field_name="subscription_id")
    customer = django_filters.UUIDFilter(field_name="customer_id")
    status = django_filters.CharFilter(field_name="status")
    method = django_filters.CharFilter(field_name="method")

    class Meta:
        model = Payment
        fields = ["subscription", "customer", "status", "method"]


class PaymentViewSet(TenantScopedViewSet):
    """Payments: create + list/retrieve (read-only after create).

    - OWNER / MANAGER can record payments.
    - All staff can view.
    - No update/delete — corrections = new payment.
    """

    queryset = Payment.objects.select_related("customer", "subscription__plan").all()
    serializer_class = PaymentListSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    filterset_class = PaymentFilter
    http_method_names = ["get", "post", "head", "options"]

    role_map = {
        "list": [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF],
        "retrieve": [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF],
        "create": [Role.OWNER, Role.MANAGER],
        "summary": [Role.OWNER, Role.MANAGER],
    }

    def get_serializer_class(self):
        if self.action == "create":
            return PaymentCreateSerializer
        return PaymentListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = PaymentService.record_payment(
                business_id=request.user.business_id,
                subscription=serializer.validated_data["subscription"],
                amount=serializer.validated_data["amount"],
                method=serializer.validated_data["method"],
                payment_date=serializer.validated_data["payment_date"],
                transaction_reference=serializer.validated_data.get("transaction_reference", ""),
                notes=serializer.validated_data.get("notes", ""),
            )
        except ValueError as e:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": str(e), "fields": {}}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            PaymentListSerializer(payment).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """GET /payments/summary/ — today, month, pending totals."""
        data = PaymentSelector.get_summary(request.user.business_id)
        return Response(data)
