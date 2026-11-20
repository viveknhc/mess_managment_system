"""Payment API (PAY-05, PAY-06)."""

import json
import logging

from django_filters import rest_framework as django_filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.payments.models import Payment
from apps.payments.serializers import PaymentCreateSerializer, PaymentListSerializer
from apps.payments.services import OnlinePaymentService, PaymentSelector, PaymentService
from common.constants import Role
from common.permissions import RoleBasedPermission
from common.viewsets import TenantScopedViewSet

logger = logging.getLogger(__name__)


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
    ordering_fields = [
        "payment_date",
        "customer__name",
        "subscription__plan__name",
        "method",
        "amount",
        "status",
        "created_at",
    ]
    http_method_names = ["get", "post", "head", "options"]

    role_map = {
        "list": [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF],
        "retrieve": [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF],
        "create": [Role.OWNER, Role.MANAGER],
        "summary": [Role.OWNER, Role.MANAGER],
    }

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == Role.CUSTOMER:
            qs = qs.filter(customer__user=self.request.user)
        return qs

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


class CustomerWebhookThrottle(AnonRateThrottle):
    scope = "customer_webhook"
    rate = "60/min"


class CustomerPaymentWebhookView(APIView):
    """POST /api/v1/webhooks/razorpay/mess/<business_id>/ — webhook from a mess's own Razorpay account.

    Records customer payments whose Checkout success never reached us (tab closed, network drop).
    No signature secret to set up: the payload is only a hint, and the payment is applied only
    after Razorpay's API confirms the capture with the owner's keys.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [CustomerWebhookThrottle]

    def post(self, request, business_id):
        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response({"status": "ignored"}, status=status.HTTP_400_BAD_REQUEST)

        if payload.get("event") not in ("payment.captured", "order.paid"):
            return Response({"status": "ignored"})
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {}) or {}
        order_id = payment.get("order_id") or ""
        if not isinstance(order_id, str) or not order_id:
            return Response({"status": "ignored"})

        try:
            applied = OnlinePaymentService.handle_webhook(business_id, order_id)
        except Exception:
            # 5xx makes Razorpay retry later
            logger.exception("Customer payment webhook failed for order %s", order_id)
            return Response({"status": "error"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"status": "ok" if applied else "ignored"})
