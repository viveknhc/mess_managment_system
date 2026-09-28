"""Customer portal API (PT-01). Self-only reads for customer role."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.deliveries.models import Delivery
from apps.deliveries.serializers import DeliveryListSerializer
from apps.payments.models import Payment
from apps.payments.serializers import PaymentListSerializer
from apps.subscriptions.models import Subscription
from apps.subscriptions.serializers import SubscriptionListSerializer
from common.constants import Role


class PortalPermission:
    """Check that user is a CUSTOMER with a linked customer profile."""

    @staticmethod
    def check(request):
        if getattr(request.user, "role", None) != Role.CUSTOMER:
            return Response(
                {"error": {"code": "PERMISSION_DENIED", "message": "Customer portal only.", "fields": {}}},
                status=403,
            )
        if not request.user.customer_profiles.exists():
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "No customer profile linked.", "fields": {}}},
                status=404,
            )
        return None


class PortalDashboardView(APIView):
    """GET /api/v1/portal/dashboard/ — customer's overview."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = PortalPermission.check(request)
        if err:
            return err
        customer = request.user.customer_profiles.first()
        subs = Subscription.objects.filter(customer=customer).select_related("plan")
        active_sub = subs.filter(status="ACTIVE").first()

        return Response(
            {
                "customer_name": customer.name,
                "active_subscription": SubscriptionListSerializer(active_sub).data if active_sub else None,
                "total_subscriptions": subs.count(),
            }
        )


class PortalSubscriptionsView(APIView):
    """GET /api/v1/portal/subscriptions/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = PortalPermission.check(request)
        if err:
            return err
        customer = request.user.customer_profiles.first()
        subs = Subscription.objects.filter(customer=customer).select_related("plan", "customer")
        return Response(SubscriptionListSerializer(subs, many=True).data)


class PortalPaymentsView(APIView):
    """GET /api/v1/portal/payments/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = PortalPermission.check(request)
        if err:
            return err
        customer = request.user.customer_profiles.first()
        payments = Payment.objects.filter(customer=customer).select_related("customer", "subscription__plan")
        return Response(PaymentListSerializer(payments, many=True).data)


class PortalDeliveriesView(APIView):
    """GET /api/v1/portal/deliveries/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = PortalPermission.check(request)
        if err:
            return err
        customer = request.user.customer_profiles.first()
        deliveries = Delivery.objects.filter(customer=customer).select_related(
            "customer", "meal", "assigned_staff"
        )[:50]
        return Response(DeliveryListSerializer(deliveries, many=True).data)


class PortalProfileView(APIView):
    """GET/PUT /api/v1/portal/profile/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = PortalPermission.check(request)
        if err:
            return err
        customer = request.user.customer_profiles.first()
        return Response(
            {
                "id": str(customer.id),
                "name": customer.name,
                "phone": customer.phone,
                "email": customer.email,
                "address": customer.address,
                "location": customer.location,
            }
        )

    def put(self, request):
        err = PortalPermission.check(request)
        if err:
            return err
        customer = request.user.customer_profiles.first()
        for field in ("phone", "email", "address", "location"):
            if field in request.data:
                setattr(customer, field, request.data[field])
        customer.save()
        return Response(
            {
                "id": str(customer.id),
                "name": customer.name,
                "phone": customer.phone,
                "email": customer.email,
                "address": customer.address,
                "location": customer.location,
            }
        )
