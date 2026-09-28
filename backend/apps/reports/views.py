"""Reports API (R-01 to R-05)."""

import datetime

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reports.selectors import (
    customer_report,
    meal_report,
    payment_report,
    revenue_report,
    subscription_report,
)
from common.constants import Role


class ReportBaseView(APIView):
    """Base: owner/manager only."""

    permission_classes = [IsAuthenticated]

    def check_role(self, request):
        role = getattr(request.user, "role", None)
        if role not in (Role.OWNER, Role.MANAGER, Role.SUPER_ADMIN):
            return Response(
                {"error": {"code": "PERMISSION_DENIED", "message": "Reports access denied.", "fields": {}}},
                status=403,
            )
        return None

    def get_date_range(self, request):
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        if date_from:
            date_from = datetime.date.fromisoformat(date_from)
        if date_to:
            date_to = datetime.date.fromisoformat(date_to)
        return date_from, date_to


class CustomerReportView(ReportBaseView):
    def get(self, request):
        err = self.check_role(request)
        if err:
            return err
        return Response(customer_report(request.user.business_id))


class SubscriptionReportView(ReportBaseView):
    def get(self, request):
        err = self.check_role(request)
        if err:
            return err
        return Response(subscription_report(request.user.business_id))


class RevenueReportView(ReportBaseView):
    def get(self, request):
        err = self.check_role(request)
        if err:
            return err
        date_from, date_to = self.get_date_range(request)
        return Response(revenue_report(request.user.business_id, date_from=date_from, date_to=date_to))


class MealReportView(ReportBaseView):
    def get(self, request):
        err = self.check_role(request)
        if err:
            return err
        date_from, date_to = self.get_date_range(request)
        return Response(meal_report(request.user.business_id, date_from=date_from, date_to=date_to))


class PaymentReportView(ReportBaseView):
    def get(self, request):
        err = self.check_role(request)
        if err:
            return err
        date_from, date_to = self.get_date_range(request)
        return Response(payment_report(request.user.business_id, date_from=date_from, date_to=date_to))
