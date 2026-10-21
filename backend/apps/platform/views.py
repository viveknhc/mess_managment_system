"""Platform billing views — public signup, business billing, SUPER_ADMIN management."""

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.businesses.models import Business
from apps.platform.models import SaasPayment, SaasPlan, SaasSubscription
from apps.platform.permissions import IsOwnerOrManager, IsSuperAdmin
from apps.platform.serializers import (
    CheckoutSerializer,
    PlatformBusinessSerializer,
    SaasPaymentSerializer,
    SaasPlanPublicSerializer,
    SaasPlanSerializer,
    SaasSubscriptionSerializer,
    SignupSerializer,
)
from apps.platform.services import PlatformService

logger = logging.getLogger(__name__)


# ── Public: Signup ────────────────────────────────────────────────────────


class SignupView(APIView):
    """Self-serve business registration — creates business + owner + trial."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # Map serializer field name to service kwarg
        data["name"] = data.pop("business_name")
        business, user = PlatformService.register_business(**data)

        # Generate JWT tokens for immediate login
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        from apps.accounts.serializers import UserSerializer

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
                "business": {"id": str(business.id), "name": business.name},
            },
            status=status.HTTP_201_CREATED,
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
    """Current billing status for the business owner."""

    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    def get(self, request):
        try:
            sub = request.user.business.saas_subscription
        except SaasSubscription.DoesNotExist:
            return Response({"error": {"code": "NOT_FOUND", "message": "No subscription found."}}, status=404)

        serializer = SaasSubscriptionSerializer(sub)
        plans = SaasPlanPublicSerializer(SaasPlan.objects.filter(is_active=True), many=True)
        return Response({"subscription": serializer.data, "available_plans": plans.data})


class CheckoutView(APIView):
    """Initiate Razorpay subscription checkout."""

    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = SaasPlan.objects.get(id=serializer.validated_data["plan_id"])
        business = request.user.business

        try:
            sub = business.saas_subscription
        except SaasSubscription.DoesNotExist:
            sub = PlatformService.start_trial(business)

        if not plan.razorpay_plan_id:
            # No Razorpay plan configured — activate directly (dev/testing)
            PlatformService.activate_subscription(sub, plan)
            return Response(
                {"message": "Plan activated.", "subscription": SaasSubscriptionSerializer(sub).data}
            )

        # Create Razorpay subscription
        from apps.platform.razorpay import RazorpayClient

        try:
            if not sub.razorpay_customer_id:
                owner = business.users.filter(role="OWNER").first()
                rz_customer = RazorpayClient.create_customer(
                    name=business.name,
                    email=owner.email if owner else "",
                    contact=owner.phone if owner else "",
                )
                sub.razorpay_customer_id = rz_customer["id"]
                sub.save(update_fields=["razorpay_customer_id"])

            rz_sub = RazorpayClient.create_subscription(
                plan_id=plan.razorpay_plan_id,
                customer_id=sub.razorpay_customer_id,
            )
            sub.razorpay_subscription_id = rz_sub["id"]
            sub.plan = plan
            sub.save(update_fields=["razorpay_subscription_id", "plan"])

            return Response(
                {
                    "razorpay_subscription_id": rz_sub["id"],
                    "razorpay_key": settings.RAZORPAY_KEY_ID,
                    "subscription": SaasSubscriptionSerializer(sub).data,
                }
            )
        except Exception as e:
            logger.exception("Razorpay checkout error")
            return Response(
                {"error": {"code": "PAYMENT_ERROR", "message": str(e), "fields": {}}},
                status=status.HTTP_502_BAD_GATEWAY,
            )


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


class PlatformBusinessViewSet(viewsets.ReadOnlyModelViewSet):
    """All businesses with billing status — SUPER_ADMIN only."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]
    serializer_class = PlatformBusinessSerializer
    queryset = Business.objects.all().prefetch_related("users")
    ordering_fields = [
        "name",
        "status",
        "saas_subscription__status",
        "saas_subscription__plan__name",
        "saas_subscription__trial_end_date",
        "created_at",
    ]

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        business = self.get_object()
        PlatformService.suspend_business(business)
        return Response({"message": f"Business '{business.name}' suspended."})

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        business = self.get_object()
        extend_days = request.data.get("extend_trial_days", 0)
        PlatformService.reactivate_business(business, extend_trial_days=int(extend_days))
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
