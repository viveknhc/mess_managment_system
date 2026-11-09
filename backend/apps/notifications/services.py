"""Notification service (N-02, N-03, N-04).

Channels: IN_APP (Notification rows) and EMAIL (daily expiry emails, idempotent
via EmailLog send markers). Interface ready for WhatsApp/SMS later.
"""

import datetime
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape

from apps.notifications.models import EmailKind, EmailLog, EmailStatus, Notification, NotificationType
from apps.subscriptions.models import Subscription
from apps.subscriptions.services import SubscriptionSelector
from common.constants import Role, SubStatus

logger = logging.getLogger(__name__)

# Subscriptions whose end_date fell within this many days before today are
# reported as "expired" in the daily digest (covers yesterday's expiries).
EXPIRED_LOOKBACK_DAYS = 1


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

        today = datetime.date.today()
        expiring = SubscriptionSelector.get_expiring(business_id).select_related("customer", "plan")

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

    # ── EMAIL channel: daily expiry emails ───────────────────────────────

    @staticmethod
    def _recently_expired(business_id, today):
        """Subs that ended in the lookback window (EXPIRED, or ACTIVE not yet swept)."""
        return Subscription.objects.filter(
            business_id=business_id,
            status__in=(SubStatus.EXPIRED, SubStatus.ACTIVE),
            end_date__lt=today,
            end_date__gte=today - timedelta(days=EXPIRED_LOOKBACK_DAYS),
        )

    @staticmethod
    def _owner_recipients(business):
        from apps.accounts.models import User

        emails = [business.email] + list(
            User.objects.filter(business_id=business.id, role=Role.OWNER, is_active=True).values_list(
                "email", flat=True
            )
        )
        seen, result = set(), []
        for e in emails:
            e = (e or "").strip()
            if e and e.lower() not in seen:
                seen.add(e.lower())
                result.append(e)
        return result

    @staticmethod
    def _send_once(*, business_id, today, kind, dedupe_key, to, subject, text, html=None):
        """Send one email unless already SENT today for this key. Never raises.

        Returns True if an email was sent on this call.
        """
        if EmailLog.objects.filter(
            business_id=business_id, ref_date=today, dedupe_key=dedupe_key, status=EmailStatus.SENT
        ).exists():
            return False

        status, error = EmailStatus.SENT, ""
        try:
            msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, to)
            if html:
                msg.attach_alternative(html, "text/html")
            msg.send(fail_silently=False)
        except Exception as exc:  # noqa: BLE001 — log and carry on with other recipients
            status, error = EmailStatus.FAILED, str(exc)[:1000]
            logger.exception("Failed to send %s email to %s (business %s)", kind, to, business_id)

        EmailLog.objects.update_or_create(
            business_id=business_id,
            ref_date=today,
            dedupe_key=dedupe_key,
            defaults={
                "kind": kind,
                "recipients": ", ".join(to),
                "subject": subject[:255],
                "status": status,
                "error": error,
            },
        )
        return status == EmailStatus.SENT

    @staticmethod
    def _line(sub):
        return f"- {sub.customer.name} ({sub.customer.customer_code}) — {sub.plan.name}, ends {sub.end_date}"

    @staticmethod
    def send_expiry_emails(business_id):
        """Daily: email owner digest + per-customer alerts for expiring/expired subs.

        Idempotent per day (EmailLog). Send failures are logged, not raised.
        Returns the number of emails sent on this call.
        """
        from apps.businesses.models import Business

        business = Business.objects.get(id=business_id)
        biz_settings = getattr(business, "settings", None)  # None if never configured
        if biz_settings is not None and not biz_settings.notify_on_expiring:
            return 0

        today = datetime.date.today()
        expiring = list(
            SubscriptionSelector.get_expiring(business_id)
            .select_related("customer", "plan")
            .order_by("end_date", "customer__name")
        )
        expired = list(
            NotificationService._recently_expired(business_id, today)
            .select_related("customer", "plan")
            .order_by("end_date", "customer__name")
        )
        if not expiring and not expired:
            return 0

        sent = 0
        name = business.name

        # 1) Owner digest — one email per business per day
        owners = NotificationService._owner_recipients(business)
        if owners:
            subject = f"[{name}] Subscription expiry digest — {today}"
            parts = [f"Daily subscription summary for {name} ({today}).", ""]
            html_parts = [f"<p>Daily subscription summary for <strong>{escape(name)}</strong> ({today}).</p>"]
            for heading, subs in (("Expiring in the next 3 days", expiring), ("Expired", expired)):
                if subs:
                    lines = [NotificationService._line(s) for s in subs]
                    parts += [f"{heading} ({len(subs)}):", *lines, ""]
                    items = "".join(f"<li>{escape(line[2:])}</li>" for line in lines)
                    html_parts.append(f"<p><strong>{heading} ({len(subs)})</strong></p><ul>{items}</ul>")
            parts.append("Log in to renew or follow up with these customers.")
            html_parts.append("<p>Log in to renew or follow up with these customers.</p>")
            if NotificationService._send_once(
                business_id=business_id,
                today=today,
                kind=EmailKind.OWNER_EXPIRY_DIGEST,
                dedupe_key="owner-digest",
                to=owners,
                subject=subject,
                text="\n".join(parts),
                html="".join(html_parts),
            ):
                sent += 1

        # 2) Customer alerts — one email per customer with an email address
        by_customer = {}
        for sub in expiring:
            by_customer.setdefault(sub.customer_id, (sub.customer, [], []))[1].append(sub)
        for sub in expired:
            by_customer.setdefault(sub.customer_id, (sub.customer, [], []))[2].append(sub)

        for customer, cust_expiring, cust_expired in by_customer.values():
            email = (customer.email or "").strip()
            if not email:
                continue
            lines = [f"Hi {customer.name},", ""]
            for sub in cust_expiring:
                lines.append(f"Your {sub.plan.name} subscription with {name} expires on {sub.end_date}.")
            for sub in cust_expired:
                lines.append(f"Your {sub.plan.name} subscription with {name} expired on {sub.end_date}.")
            lines += ["", f"Please contact {name} to renew and keep your meals coming.", "", f"— {name}"]
            subject = (
                f"Your {name} subscription is expiring soon"
                if cust_expiring
                else f"Your {name} subscription has expired"
            )
            if NotificationService._send_once(
                business_id=business_id,
                today=today,
                kind=EmailKind.CUSTOMER_EXPIRY,
                dedupe_key=f"customer:{customer.id}",
                to=[email],
                subject=subject,
                text="\n".join(lines),
            ):
                sent += 1

        return sent
