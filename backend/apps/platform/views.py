"""Platform billing views — business billing, SUPER_ADMIN onboarding and payment recording."""

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.businesses.models import Business
from apps.platform.models import SaasPayment, SaasPlan, SaasSubscription
from apps.platform.permissions import IsOwner, IsOwnerOrManager, IsSuperAdmin
from apps.platform.serializers import (
    CreateBusinessSerializer,
    PlatformBusinessSerializer,
    RecordPaymentSerializer,
    SaasPaymentSerializer,
    SaasPlanPublicSerializer,
    SaasPlanSerializer,
    SaasSubscriptionSerializer,
)
from apps.platform.services import PlatformService

logger = logging.getLogger(__name__)


def _validation_error(message):
    return Response(
        {"error": {"code": "VALIDATION_ERROR", "message": message, "fields": {}}},
        status=status.HTTP_400_BAD_REQUEST,
    )


# ── Public: Plans listing ─────────────────────────────────────────────────


class PublicPlansView(generics.ListAPIView):
    """Public pricing page — active plans only, no Razorpay IDs."""

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = SaasPlanPublicSerializer
    queryset = SaasPlan.objects.filter(is_active=True)
    pagination_class = None


# ── Business Owner: Billing ───────────────────────────────────────────────


class BillingView(APIView):
    """Current billing status, amount due and payment history for the business owner."""

    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    def get(self, request):
        try:
            sub = SaasSubscription.objects.select_related("business", "plan").get(
                business=request.user.business
            )
        except SaasSubscription.DoesNotExist:
            return Response({"error": {"code": "NOT_FOUND", "message": "No subscription found."}}, status=404)

        payments = SaasPayment.objects.filter(business=request.user.business, status="PAID")
        return Response(
            {
                "subscription": SaasSubscriptionSerializer(sub).data,
                "payments": SaasPaymentSerializer(payments, many=True).data,
            }
        )


class BillingCancelView(APIView):
    """Owner cancels the monthly plan. Access continues until the paid month ends."""

    permission_classes = [IsAuthenticated, IsOwner]

    def post(self, request):
        try:
            sub = request.user.business.saas_subscription
        except SaasSubscription.DoesNotExist:
            return Response({"error": {"code": "NOT_FOUND", "message": "No subscription found."}}, status=404)
        try:
            PlatformService.cancel_subscription(sub)
        except ValueError as e:
            return _validation_error(str(e))
        return Response({"subscription": SaasSubscriptionSerializer(sub).data})


# ── Razorpay Webhook ──────────────────────────────────────────────────────


@method_decorator(csrf_exempt, name="dispatch")
class RazorpayWebhookView(APIView):
    """Razorpay webhook — verifies signature, dispatches to PlatformService."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        signature = request.headers.get("X-Razorpay-Signature", "")
        body = request.body

        # Verify signature
        webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
        if webhook_secret:
            expected = hmac.new(
                webhook_secret.encode("utf-8"),
                body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, signature):
                return JsonResponse({"error": "Invalid signature"}, status=400)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        event = payload.get("event", "")
        entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})
        rz_sub_id = entity.get("id", "")

        if not rz_sub_id:
            return JsonResponse({"status": "ignored"})

        try:
            sub = SaasSubscription.objects.select_related("business", "plan").get(
                razorpay_subscription_id=rz_sub_id,
            )
        except SaasSubscription.DoesNotExist:
            logger.warning("Webhook for unknown subscription: %s", rz_sub_id)
            return JsonResponse({"status": "ignored"})

        if event == "subscription.activated":
            if sub.plan:
                PlatformService.activate_subscription(sub, sub.plan)

        elif event == "subscription.charged":
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            amount = payment_entity.get("amount", 0) / 100  # paise to rupees
            PlatformService.record_payment_success(
                sub,
                amount=amount,
                razorpay_payment_id=payment_entity.get("id", ""),
                razorpay_order_id=payment_entity.get("order_id", ""),
            )

        elif event == "subscription.payment_failed":
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            amount = payment_entity.get("amount", 0) / 100
            PlatformService.record_payment_failure(
                sub,
                amount=amount,
                failure_reason=payment_entity.get("error_description", ""),
                razorpay_payment_id=payment_entity.get("id", ""),
            )

        elif event == "subscription.cancelled":
            PlatformService.suspend_business(sub.business)

        return JsonResponse({"status": "ok"})


# ── SUPER_ADMIN: Platform Management ─────────────────────────────────────


class PlatformBusinessViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """All businesses with billing status; onboarding and payments — SUPER_ADMIN only."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]
    serializer_class = PlatformBusinessSerializer
    queryset = Business.objects.all().select_related("saas_subscription__plan").prefetch_related("users")
    ordering_fields = [
        "name",
        "status",
        "saas_subscription__status",
        "saas_subscription__plan__name",
        "saas_subscription__trial_end_date",
        "saas_subscription__current_period_end",
        "created_at",
    ]

    def create(self, request, *args, **kwargs):
        serializer = CreateBusinessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        data["name"] = data.pop("business_name")
        business, _owner = PlatformService.create_business(**data)
        return Response(PlatformBusinessSerializer(business).data, status=status.HTTP_201_CREATED)

    def _subscription(self, business):
        try:
            return business.saas_subscription
        except SaasSubscription.DoesNotExist:
            return PlatformService.start_billing(business)

    @action(detail=True, methods=["post"], url_path="record-payment")
    def record_payment(self, request, pk=None):
        business = self.get_object()
        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = PlatformService.record_manual_payment(
                self._subscription(business), recorded_by=request.user, **serializer.validated_data
            )
        except ValueError as e:
            return _validation_error(str(e))
        return Response(SaasPaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        business = self.get_object()
        try:
            PlatformService.cancel_subscription(self._subscription(business))
        except ValueError as e:
            return _validation_error(str(e))
        return Response({"message": f"Monthly plan for '{business.name}' cancelled."})

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        business = self.get_object()
        PlatformService.suspend_business(business)
        return Response({"message": f"Business '{business.name}' suspended."})

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        business = self.get_object()
        PlatformService.reactivate_business(business)
        return Response({"message": f"Business '{business.name}' reactivated."})


class PlatformPlanViewSet(viewsets.ModelViewSet):
    """CRUD SaaS plan tiers — SUPER_ADMIN only."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]
    serializer_class = SaasPlanSerializer
    queryset = SaasPlan.objects.all()
    ordering_fields = ["name", "price_monthly", "max_customers", "max_staff", "is_active", "created_at"]


class PlatformPaymentListView(generics.ListAPIView):
    """All billing transactions — SUPER_ADMIN only."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]
    serializer_class = SaasPaymentSerializer
    queryset = SaasPayment.objects.all().select_related("business", "plan")
    ordering_fields = ["created_at", "business__name", "plan__name", "amount", "status", "period_start"]


class PlatformStatsView(APIView):
    """Platform-wide stats — SUPER_ADMIN only."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        return Response(PlatformService.get_platform_stats())
