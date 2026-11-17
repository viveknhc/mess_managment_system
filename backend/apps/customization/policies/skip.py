"""Skip policies — what a skipped meal does to the subscription (extension point ``skip``).

``apply(skip)`` runs inside DeliveryService.skip_meal's transaction, after the
delivery is SKIPPED and the MealSkip row exists.
"""

from apps.customization.registry import SKIP, Policy, extension_point
from apps.deliveries.models import SkipAdjustment

_point = extension_point(SKIP)


@_point.register
class NoAdjustmentSkip(Policy):
    key = "NONE"
    label = "No adjustment"
    description = "The skipped meal is lost; the subscription is unchanged."

    def apply(self, skip):
        pass


@_point.register
class ExtendSkip(Policy):
    key = "EXTEND"
    label = "Extend end date"
    description = "The subscription ends one day later and the meal is delivered then."

    def apply(self, skip):
        from apps.deliveries.services import DeliveryService
        from apps.subscriptions.services import SubscriptionService

        skip.adjustment = SkipAdjustment.EXTEND
        skip.save(update_fields=["adjustment", "updated_at"])
        subscription = SubscriptionService.extend_end_date(skip.subscription, days=1)
        DeliveryService.generate_delivery_schedule(subscription)
