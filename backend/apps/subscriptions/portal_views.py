"""Customer portal API (PT-01, PT-09). Self-only reads + actions for customer role.

Every view re-derives the customer profile from request.user — a customer can
only ever see and act on their own rows. Staff/admin APIs are unreachable here.
"""

import datetime

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle
from rest_framework.views import APIView

from apps.deliveries.models import Delivery, DeliveryStatus
from apps.deliveries.serializers import DeliveryListSerializer
from apps.deliveries.services import DeliveryService
from apps.payments.models import Payment
from apps.payments.serializers import PaymentListSerializer
from apps.subscriptions.models import Subscription
from apps.subscriptions.serializers import SubscriptionListSerializer
from apps.subscriptions.services import SubscriptionService
from common.constants import Role, SubStatus


class PortalRateThrottle(ScopedRateThrottle):
    """Portal reads — 120/min (arch. §15)."""

    scope = "reads"


class PortalWriteThrottle(SimpleRateThrottle):
    """Portal writes (skip/pause/renew) — 20/min per user (PT-09)."""

    scope = "portal_writes"
    rate = "20/min"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return self.cache_format % {"scope": self.scope, "ident": request.user.pk}
        return None


def _error(code, message, status_code):
    return Response({"error": {"code": code, "message": message, "fields": {}}}, status=status_code)


class PortalPermission:
    """Check that user is a CUSTOMER with a linked customer profile."""

    @staticmethod
    def check(request):
        if getattr(request.user, "role", None) != Role.CUSTOMER:
            return _error("PERMISSION_DENIED", "Customer portal only.", 403)
        if not request.user.customer_profiles.exists():
            return _error("NOT_FOUND", "No customer profile linked.", 404)
        return None


def _portal_customer(request):
    """Resolve the customer profile for this request, or return an error response."""
    err = PortalPermission.check(request)
    if err:
        return None, err
    return request.user.customer_profiles.select_related("business").first(), None


def _get_own_subscription(customer, sub_id):
    """Fetch a subscription owned by this customer only — foreign IDs are 404."""
    return (
        Subscription.objects.select_related("plan", "customer").filter(id=sub_id, customer=customer).first()
    )


class PortalDashboardView(APIView):
    """GET /api/v1/portal/dashboard/ — greeting, current plan, days remaining,
    today's meal status (PT-03)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [PortalRateThrottle]

    def get(self, request):
        customer, err = _portal_customer(request)
        if err:
            return err
        subs = Subscription.objects.filter(customer=customer).select_related("plan")
        active_sub = (
            subs.filter(status__in=[SubStatus.ACTIVE, SubStatus.PAUSED]).order_by("-end_date").first()
        )

        todays_meal = None
        if active_sub:
            delivery = (
                Delivery.objects.filter(subscription=active_sub, delivery_date=datetime.date.today())
                .select_related("meal")
                .first()
            )
            if delivery:
                todays_meal = {
                    "id": str(delivery.id),
                    "meal_name": delivery.meal.name,
                    "delivery_date": str(delivery.delivery_date),
                    "status": delivery.status,
                    "skippable": delivery.status == DeliveryStatus.PENDING,
                }

        return Response(
            {
                "customer_name": customer.name,
                "active_subscription": (SubscriptionListSerializer(active_sub).data if active_sub else None),
                "todays_meal": todays_meal,
                "total_subscriptions": subs.count(),
            }
        )


class PortalSubscriptionsView(APIView):
    """GET /api/v1/portal/subscriptions/ — my subscriptions only."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [PortalRateThrottle]

    def get(self, request):
        customer, err = _portal_customer(request)
        if err:
            return err
        subs = Subscription.objects.filter(customer=customer).select_related("plan", "customer")
        return Response(SubscriptionListSerializer(subs, many=True).data)


class PortalSubscriptionActionsView(APIView):
    """Customer actions on their OWN subscription (PT-01, PT-04).

    POST /api/v1/portal/subscriptions/{id}/skip/      {date?, reason?}
    POST /api/v1/portal/subscriptions/{id}/pause-request/  {start_date, end_date?, reason?}
    POST /api/v1/portal/subscriptions/{id}/renew/
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [PortalWriteThrottle]

    def _dispatch(self, request, sub_id, action):
        customer, err = _portal_customer(request)
        if err:
            return err
        sub = _get_own_subscription(customer, sub_id)
        if not sub:
            return _error("NOT_FOUND", "Subscription not found.", 404)

        try:
            if action == "skip":
                return self._skip(request, customer, sub)
            if action == "pause":
                return self._pause_request(request, sub)
            return self._renew(sub)
        except ValueError as e:
            return _error("VALIDATION_ERROR", str(e), 400)

    def _skip(self, request, customer, sub):
        """Skip a PENDING delivery belonging to this subscription."""
        date_str = request.data.get("date")
        reason = request.data.get("reason", "")
        target_date = None
        if date_str:
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                return _error("VALIDATION_ERROR", "Invalid date format, use YYYY-MM-DD.", 400)
            if target_date < datetime.date.today():
                return _error("VALIDATION_ERROR", "Cannot skip a past date.", 400)

        deliveries = Delivery.objects.filter(
            subscription=sub,
            status=DeliveryStatus.PENDING,
            delivery_date__gte=target_date or datetime.date.today(),
        ).order_by("delivery_date")
        if not deliveries.exists():
            return _error("VALIDATION_ERROR", "No upcoming delivery found to skip.", 400)
        if not sub.plan.skip_allowed:
            return _error("VALIDATION_ERROR", "Skipping is not allowed on this plan.", 400)

        skip = DeliveryService.skip_meal(deliveries.first(), reason=reason)
        return Response({"id": str(skip.id), "skip_date": str(skip.skip_date), "reason": skip.reason})

    def _pause_request(self, request, sub):
        """Pause the subscription for a date range (min/max per business settings)."""
        start_str = request.data.get("start_date")
        if not start_str:
            return _error("VALIDATION_ERROR", "start_date is required.", 400)
        try:
            start_date = datetime.date.fromisoformat(start_str)
        except ValueError:
            return _error("VALIDATION_ERROR", "Invalid start_date format, use YYYY-MM-DD.", 400)
        if start_date < datetime.date.today():
            return _error("VALIDATION_ERROR", "Pause start date cannot be in the past.", 400)

        end_str = request.data.get("end_date")
        try:
            end_date = datetime.date.fromisoformat(end_str) if end_str else start_date
        except ValueError:
            return _error("VALIDATION_ERROR", "Invalid end_date format, use YYYY-MM-DD.", 400)
        if end_date < start_date:
            return _error("VALIDATION_ERROR", "end_date cannot be before start_date.", 400)

        days = (end_date - start_date).days + 1
        settings_row = getattr(sub.business, "settings", None)
        min_days = settings_row.min_pause_days if settings_row else 1
        max_days = settings_row.max_pause_days if settings_row else 7
        if days < min_days:
            return _error("VALIDATION_ERROR", f"Minimum pause duration is {min_days} day(s).", 400)
        if days > max_days:
            return _error("VALIDATION_ERROR", f"Maximum pause duration is {max_days} day(s).", 400)
        if not sub.plan.pause_allowed:
            return _error("VALIDATION_ERROR", "Pausing is not allowed on this plan.", 400)

        # Pause flow (D-10): flip status via state machine, cancel deliveries in range.
        SubscriptionService.pause(sub)
        DeliveryService.pause_deliveries(
            sub, start_date=start_date, end_date=end_date, reason=request.data.get("reason", "")
        )
        return Response(SubscriptionListSerializer(sub).data)

    def _renew(self, sub):
        """Renew an EXPIRED/CANCELLED subscription — new PENDING row linked back."""
        new_sub = SubscriptionService.renew(sub)
        return Response(SubscriptionListSerializer(new_sub).data, status=201)

    def post(self, request, sub_id=None, action=None):
        return self._dispatch(request, sub_id, action)


class PortalPaymentsView(APIView):
    """GET /api/v1/portal/payments/ — my payment history (PT-05)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [PortalRateThrottle]

    def get(self, request):
        customer, err = _portal_customer(request)
        if err:
            return err
        payments = Payment.objects.filter(customer=customer).order_by("-payment_date")
        return Response(PaymentListSerializer(payments[:100], many=True).data)


class PortalDeliveriesView(APIView):
    """GET /api/v1/portal/deliveries/ — my delivery history (PT-05)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [PortalRateThrottle]

    def get(self, request):
        customer, err = _portal_customer(request)
        if err:
            return err
        deliveries = (
            Delivery.objects.filter(customer=customer)
            .select_related("customer", "meal", "assigned_staff")
            .order_by("-delivery_date")[:100]
        )
        return Response(DeliveryListSerializer(deliveries, many=True).data)


class PortalProfileView(APIView):
    """GET/PUT /api/v1/portal/profile/ — view/edit limited fields (PT-06)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [PortalRateThrottle]

    EDITABLE_FIELDS = ("phone", "email", "address", "location")

    @staticmethod
    def _payload(customer):
        return {
            "id": str(customer.id),
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email,
            "address": customer.address,
            "location": customer.location,
        }

    def get(self, request):
        customer, err = _portal_customer(request)
        if err:
            return err
        return Response(self._payload(customer))

    def put(self, request):
        customer, err = _portal_customer(request)
        if err:
            return err
        for field in self.EDITABLE_FIELDS:
            if field in request.data:
                setattr(customer, field, request.data[field])
        customer.save(update_fields=[*self.EDITABLE_FIELDS, "updated_at"])
        return Response(self._payload(customer))
