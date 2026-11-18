"""Seed three more demo messes of different kinds, for checking per-mess customization.

Each mess is on a different MessDeck plan (different features) and has its own
workflow rules, staff, meal plans, customers and subscriptions:

- Sharma Tiffin Service      — Starter plan: core only (no portal, online payments, reports); skip = no adjustment
- Green Valley Hostel Mess   — Standard plan: portal + reports; online payments switched ON for this mess only;
                               skip = extend end date
- TechPark Corporate Canteen — Pro plan: everything; customer portal switched OFF for this mess only

Annapurna Mess (seed_data) is left untouched. All new logins use the password ``demo123``.

Usage:
    python manage.py seed_messes           # create the messes that don't exist yet
    python manage.py seed_messes --reset   # delete these three messes and create them again
"""

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.customization.registry import CUSTOMER_PORTAL, ONLINE_PAYMENTS, REPORTS, SKIP
from apps.customization.services import FeatureService, PolicyService
from apps.deliveries.models import Delivery
from apps.meals.models import Meal
from apps.payments.models import Payment
from apps.payments.services import PaymentService
from apps.plans.models import Plan
from apps.platform.models import PaymentMethod, SaasPlan
from apps.platform.services import PlatformService
from apps.settings_app.models import BusinessSettings
from apps.subscriptions.models import Subscription
from apps.subscriptions.services import SubscriptionService
from common.constants import Role

PASSWORD = "demo123"

SAAS_PLANS = [
    {
        "name": "Starter",
        "price_monthly": Decimal("299.00"),
        "setup_fee": Decimal("1000.00"),
        "reactivation_fee": Decimal("500.00"),
        "max_customers": 50,
        "max_staff": 2,
        "features": ["Customers, plans, subscriptions", "Payments & deliveries", "Up to 50 customers"],
        "feature_keys": [],
    },
    {
        "name": "Standard",
        "price_monthly": Decimal("599.00"),
        "setup_fee": Decimal("2000.00"),
        "reactivation_fee": Decimal("1000.00"),
        "max_customers": 200,
        "max_staff": 5,
        "features": ["Everything in Starter", "Customer portal", "Reports", "Up to 200 customers"],
        "feature_keys": [CUSTOMER_PORTAL, REPORTS],
    },
    {
        "name": "Pro",
        "price_monthly": Decimal("999.00"),
        "setup_fee": Decimal("2500.00"),
        "reactivation_fee": Decimal("1500.00"),
        "max_customers": 0,
        "max_staff": 0,
        "features": ["Everything in Standard", "Online payments (Razorpay)", "Unlimited customers & staff"],
        "feature_keys": [CUSTOMER_PORTAL, ONLINE_PAYMENTS, REPORTS],
    },
]

MESSES = [
    {
        "name": "Sharma Tiffin Service",
        "kind": "Home tiffin service",
        "saas_plan": "Starter",
        "phone": "9811000001",
        "email": "orders@sharmatiffin.in",
        "address": "B-14, Lajpat Nagar, Delhi",
        "owner": ("tiffin_owner", "Sunita Sharma", "sunita@sharmatiffin.in"),
        "staff": [("tiffin_delivery", "Raju Delivery", Role.DELIVERY_STAFF)],
        "skip": "NONE",
        "feature_overrides": {},
        "settings": {"min_pause_days": 2, "max_pause_days": 5},
        "plans": [
            ("Veg Lunch Tiffin – 30 days", "Tiffin", 30, 30, "1800.00", True, False),
            ("Lunch + Dinner Tiffin – 30 days", "Tiffin", 30, 60, "3200.00", True, True),
        ],
        "customers": [
            ("Amit Verma", "9811100001", "Lajpat Nagar"),
            ("Neha Gupta", "9811100002", "Defence Colony"),
            ("Rohit Malhotra", "9811100003", "Jangpura"),
            ("Pooja Arora", "9811100004", "Lajpat Nagar"),
        ],
        "portal_customer": None,
    },
    {
        "name": "Green Valley Hostel Mess",
        "kind": "Student hostel mess",
        "saas_plan": "Standard",
        "phone": "9822000001",
        "email": "mess@greenvalleyhostel.in",
        "address": "Near VIT Gate 2, Pune",
        "owner": ("hostel_owner", "Prakash Patil", "prakash@greenvalleyhostel.in"),
        "staff": [
            ("hostel_manager", "Kavita Joshi", Role.MANAGER),
            ("hostel_kitchen", "Ganesh Cook", Role.KITCHEN_STAFF),
        ],
        "skip": "EXTEND",
        "feature_overrides": {ONLINE_PAYMENTS: True},  # extra for this mess, beyond its plan
        "settings": {"min_pause_days": 3, "max_pause_days": 15},
        "plans": [
            ("Semester Full Board", "Lunch", 120, 120, "10500.00", True, True),
            ("Monthly Breakfast", "Breakfast", 30, 30, "900.00", True, False),
            ("Monthly Lunch + Dinner", "Dinner", 30, 30, "3000.00", True, True),
        ],
        "customers": [
            ("Aditya Kulkarni", "9822100001", "Room 101"),
            ("Sneha Deshmukh", "9822100002", "Room 104"),
            ("Varun Nair", "9822100003", "Room 210"),
            ("Ishita Rao", "9822100004", "Room 215"),
            ("Karan Mehta", "9822100005", "Room 302"),
        ],
        "portal_customer": ("hostel_student", "Aditya Kulkarni"),
    },
    {
        "name": "TechPark Corporate Canteen",
        "kind": "Corporate canteen",
        "saas_plan": "Pro",
        "phone": "9833000001",
        "email": "canteen@techpark.in",
        "address": "Tower C, Whitefield, Bengaluru",
        "owner": ("canteen_owner", "Meera Iyer", "meera@techparkcanteen.in"),
        "staff": [
            ("canteen_manager", "Arjun Reddy", Role.MANAGER),
            ("canteen_delivery", "Suresh Runner", Role.DELIVERY_STAFF),
            ("canteen_kitchen", "Lakshmi Chef", Role.KITCHEN_STAFF),
        ],
        "skip": "NONE",
        "feature_overrides": {CUSTOMER_PORTAL: False},  # employees don't log in; the company pays
        "settings": {"min_pause_days": 1, "max_pause_days": 30},
        "plans": [
            ("Weekday Lunch – Monthly", "Lunch", 30, 22, "2200.00", False, True),
            ("Breakfast + Lunch – Monthly", "Breakfast", 30, 44, "3900.00", False, True),
        ],
        "customers": [
            ("Infosys Team A (Floor 3)", "9833100001", "Tower C, Floor 3"),
            ("Wipro Analytics Desk", "9833100002", "Tower A, Floor 7"),
            ("Ravi Shankar", "9833100003", "Tower C, Floor 5"),
            ("Divya Menon", "9833100004", "Tower B, Floor 2"),
        ],
        "portal_customer": None,
    },
]


class Command(BaseCommand):
    help = "Create three more demo messes with different MessDeck plans, features and workflow rules"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete these demo messes first")

    def handle(self, **options):
        names = [m["name"] for m in MESSES]
        if options["reset"]:
            deleted = self._delete(Business.objects.filter(name__in=names))
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} demo mess(es)."))

        plans = self._saas_plans()
        for spec in MESSES:
            if Business.objects.filter(name=spec["name"]).exists():
                self.stdout.write(f"Skipped {spec['name']} (already exists; use --reset to recreate)")
                continue
            with transaction.atomic():
                self._create_mess(spec, plans[spec["saas_plan"]])
            self.stdout.write(
                self.style.SUCCESS(f"Created {spec['name']} ({spec['kind']}, {spec['saas_plan']})")
            )
        self._print_summary()

    @transaction.atomic
    def _delete(self, businesses):
        """Delete only these messes. Meals and meal plans are PROTECTed, so remove what uses them first."""
        ids = list(businesses.values_list("id", flat=True))
        Delivery.objects.filter(business_id__in=ids).delete()
        Payment.objects.filter(business_id__in=ids).delete()
        Subscription.objects.filter(business_id__in=ids).delete()
        Plan.objects.filter(business_id__in=ids).delete()
        Meal.objects.filter(business_id__in=ids).delete()
        User.objects.filter(business_id__in=ids).delete()
        Business.objects.filter(id__in=ids).delete()
        return len(ids)

    def _saas_plans(self):
        plans = {}
        for spec in SAAS_PLANS:
            plan, _ = SaasPlan.objects.update_or_create(name=spec["name"], defaults=spec)
            plans[spec["name"]] = plan
        return plans

    def _create_mess(self, spec, saas_plan):
        username, owner_name, owner_email = spec["owner"]
        biz, owner = PlatformService.create_business(
            name=spec["name"],
            owner_username=username,
            owner_password=PASSWORD,
            owner_name=owner_name,
            owner_email=owner_email,
            owner_phone=spec["phone"],
            phone=spec["phone"],
            email=spec["email"],
            address=spec["address"],
        )

        # MessDeck billing: this mess's plan, first payment (setup + first month) received.
        sub = biz.saas_subscription
        sub.plan = saas_plan
        sub.save(update_fields=["plan", "updated_at"])
        PlatformService.record_manual_payment(
            sub, amount=PlatformService.amount_due(sub).total, method=PaymentMethod.UPI, reference="DEMO"
        )

        # What a SUPER_ADMIN would set under Businesses → Customize.
        PolicyService.set_policy(biz.id, SKIP, spec["skip"])
        if spec["feature_overrides"]:
            FeatureService.set_overrides(biz.id, spec["feature_overrides"])
        BusinessSettings.objects.create(business=biz, **spec["settings"])

        for staff_username, name, role in spec["staff"]:
            User.objects.create_user(
                username=staff_username,
                password=PASSWORD,
                name=name,
                role=role,
                business=biz,
                email=f"{staff_username}@example.com",
            )

        meals = {m.name: m for m in Meal.objects.filter(business=biz)}
        meal_plans = [
            Plan.objects.create(
                business=biz,
                name=name,
                meal=meals[meal],
                duration_days=days,
                total_meals=total,
                price=Decimal(price),
                skip_allowed=skip,
                pause_allowed=pause,
            )
            for name, meal, days, total, price, skip, pause in spec["plans"]
        ]

        portal_username, portal_name = spec["portal_customer"] or (None, None)
        today = timezone.localdate()
        for i, (name, phone, location) in enumerate(spec["customers"]):
            user = None
            if name == portal_name:
                user = User.objects.create_user(
                    username=portal_username,
                    password=PASSWORD,
                    name=name,
                    role=Role.CUSTOMER,
                    business=biz,
                    email=f"{portal_username}@example.com",
                )
            customer = Customer.objects.create(
                business=biz,
                name=name,
                phone=phone,
                email=f"{phone}@example.com",
                address=spec["address"],
                location=location,
                user=user,
            )
            plan = meal_plans[i % len(meal_plans)]
            subscription = SubscriptionService.create_subscription(
                business_id=biz.id, customer=customer, plan=plan, start_date=today - timedelta(days=i * 3)
            )
            if i == len(spec["customers"]) - 1:
                continue  # last customer stays PENDING (not paid yet)
            # Second customer has paid half so far — still PENDING, shows partial payment.
            amount = plan.price / 2 if i == 1 else plan.price
            PaymentService.record_payment(
                business_id=biz.id,
                subscription=subscription,
                amount=amount,
                method="UPI" if i % 2 == 0 else "CASH",
                payment_date=today - timedelta(days=i * 3),
            )

    def _print_summary(self):
        self.stdout.write("")
        self.stdout.write(f"All logins below use the password: {PASSWORD}")
        for spec in MESSES:
            biz = Business.objects.filter(name=spec["name"]).first()
            if biz is None:
                continue
            features = sorted(FeatureService.enabled(biz.id)) or ["(core only)"]
            logins = [spec["owner"][0], *(s[0] for s in spec["staff"])]
            if spec["portal_customer"]:
                logins.append(spec["portal_customer"][0])
            self.stdout.write(
                f"  {spec['name']} [{spec['saas_plan']}] skip={PolicyService.get(biz.id, SKIP).key} "
                f"features={', '.join(features)}\n    logins: {', '.join(logins)}"
            )
