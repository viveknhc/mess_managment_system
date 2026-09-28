"""Notification service (N-02, N-03, N-04).

IN_APP channel for now. Interface ready for WhatsApp/SMS/Email later.
"""

import datetime
from datetime import timedelta

from apps.notifications.models import Notification, NotificationType
from apps.subscriptions.models import Subscription
from common.constants import SubStatus


class NotificationService:
    @staticmethod
    def emit(*, business_id, user, notification_type, title, message):
        """Create an in-app notification. Single channel for MVP."""
        return Notification.objects.create(
            business_id=business_id,
            user=user,
            type=notification_type,
            title=title,
            message=message,
        )

    @staticmethod
    def emit_payment_received(*, business_id, user, amount, customer_name):
        return NotificationService.emit(
            business_id=business_id,
            user=user,
            notification_type=NotificationType.PAYMENT_RECEIVED,
            title="Payment Received",
            message=f"₹{amount} received from {customer_name}.",
        )

    @staticmethod
    def emit_subscription_activated(*, business_id, user, customer_name, plan_name):
        return NotificationService.emit(
            business_id=business_id,
            user=user,
            notification_type=NotificationType.SUBSCRIPTION_ACTIVATED,
            title="Subscription Activated",
            message=f"{customer_name} is now active on {plan_name}.",
        )

    @staticmethod
    def emit_expiring_notifications(business_id):
        """Nightly: notify owners about expiring subscriptions (N-04)."""
        from apps.accounts.models import User
        from common.constants import Role

        today = datetime.date.today()
        expiring = Subscription.objects.filter(
            business_id=business_id,
            status=SubStatus.ACTIVE,
            end_date__gte=today,
            end_date__lte=today + timedelta(days=3),
        ).select_related("customer", "plan")

        owners = User.objects.filter(business_id=business_id, role=Role.OWNER, is_active=True)
        created = 0

        for sub in expiring:
            # Avoid duplicate notifications for the same subscription on the same day
            for owner in owners:
                exists = Notification.objects.filter(
                    user=owner,
                    type=NotificationType.SUBSCRIPTION_EXPIRING,
                    message__contains=str(sub.id),
                    sent_at__date=today,
                ).exists()
                if not exists:
                    NotificationService.emit(
                        business_id=business_id,
                        user=owner,
                        notification_type=NotificationType.SUBSCRIPTION_EXPIRING,
                        title="Subscription Expiring Soon",
                        message=f"{sub.customer.name}'s {sub.plan.name} expires on {sub.end_date}. Sub ID: {sub.id}",
                    )
                    created += 1

        return created
