"""Give demo customers food customizations so the kitchen page shows extra-food totals.

Picks customers who have a meal today (ACTIVE subscription, delivery today) and adds
extras like "Extra chicken 100g" through SubscriptionService.customize — so each extra
is charged for the meals left, exactly as when an owner adds it. Also switches on the
custom_subscriptions feature for those messes so owners can see and edit them.

Usage:
    python manage.py seed_customizations                          # every business
    python manage.py seed_customizations --business "Green Valley Hostel Mess"
    python manage.py seed_customizations --replace                # redo customers who already have extras

DEMO ONLY: it changes real subscriptions and their bills. It refuses to run when DEBUG is off
(production) unless --allow-production is passed.
"""

import datetime
import random

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.businesses.models import Business
from apps.customization.registry import CUSTOM_SUBSCRIPTIONS
from apps.customization.services import FeatureService
from apps.deliveries.models import Delivery, DeliveryStatus
from apps.subscriptions.services import SubscriptionService
from common.constants import SubStatus

# (label, ₹ per meal), weighted by how often messes see them.
EXTRAS = [
    ("Extra chicken 100g", "30"),
    ("Extra chicken 100g", "30"),
    ("Extra chicken 150g", "45"),
    ("Extra rice 100g", "10"),
    ("Add 2 chapati", "10"),
    ("Extra egg 2 pcs", "16"),
    ("Extra curd 100ml", "10"),
    ("Fish fry 1 pc", "40"),
]
REQUESTS = [("No rice", "0"), ("Less spicy", "0"), ("No onion", "0")]


class Command(BaseCommand):
    help = "Seed food customizations on today's customers (kitchen extra-food totals)."

    def add_arguments(self, parser):
        parser.add_argument("--business", help="Only this business (exact name)")
        parser.add_argument("--replace", action="store_true", help="Replace existing customizations")
        parser.add_argument("--share", type=float, default=0.6, help="Share of customers to customize")
        parser.add_argument(
            "--allow-production",
            action="store_true",
            help="Run even with DEBUG off — adds fake extras to REAL customers and charges them",
        )

    def handle(self, **options):
        if not settings.DEBUG and not options["allow_production"]:
            raise CommandError(
                "Demo data only — this adds extras to real subscriptions and charges customers. "
                "DEBUG is off (production?). Pass --allow-production if you really mean it."
            )
        rng = random.Random(42)
        businesses = Business.objects.order_by("name")
        if options["business"]:
            businesses = businesses.filter(name=options["business"])
            if not businesses.exists():
                raise CommandError(f'No business named "{options["business"]}".')

        today = datetime.date.today()
        for biz in businesses:
            subs = {
                d.subscription
                for d in Delivery.objects.filter(
                    business=biz,
                    delivery_date=today,
                    status__in=[DeliveryStatus.PENDING, DeliveryStatus.OUT_FOR_DELIVERY],
                    subscription__status=SubStatus.ACTIVE,
                ).select_related("subscription__customer", "subscription__plan")
            }
            done = 0
            for sub in sorted(subs, key=lambda s: s.customer.name):
                if sub.items.exists() and not options["replace"]:
                    continue
                if rng.random() > options["share"]:
                    continue
                items = [rng.choice(EXTRAS)]
                if rng.random() < 0.3:
                    items.append(rng.choice(EXTRAS))
                if rng.random() < 0.25:
                    items.append(rng.choice(REQUESTS))
                unique = list(dict.fromkeys(items))  # same extra twice → once
                with transaction.atomic():
                    SubscriptionService.customize(
                        sub, items=[{"label": label, "price_per_meal": price} for label, price in unique]
                    )
                done += 1
            if done:
                FeatureService.set_overrides(biz.id, {CUSTOM_SUBSCRIPTIONS: True})
            self.stdout.write(f"  {biz.name}: {done} of {len(subs)} customers with a meal today customized")
        self.stdout.write(self.style.SUCCESS("Customizations seeded."))
