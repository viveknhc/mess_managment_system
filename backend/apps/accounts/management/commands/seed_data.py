"""Seed realistic demo data for one business (SD-01).

Creates a full "Annapurna Mess" business with staff, customers, plans,
subscriptions in every state, payments, deliveries, skips, pauses,
notifications, and audit log entries.

Usage:
    python manage.py seed_data           # Seed (fails if already exists)
    python manage.py seed_data --reset   # Flush + re-seed
"""

import datetime
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.audit.services import AuditService
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.deliveries.models import Delivery, DeliveryStatus, MealSkip, SubscriptionPause
from apps.deliveries.services import DeliveryService
from apps.meals.models import Meal
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.payments.models import Payment, PaymentMethod
from apps.payments.services import PaymentService
from apps.plans.models import Plan
from apps.settings_app.models import BusinessSettings, SkipRule
from apps.subscriptions.models import Subscription
from apps.subscriptions.services import SubscriptionService
from common.constants import Role, Status, SubStatus

BUSINESS_NAME = "Annapurna Mess"

TODAY = datetime.date.today()

CUSTOMER_DATA = [
    {
        "name": "Rahul Kumar",
        "phone": "9876543210",
        "address": "Flat 101, Koregaon Park, Pune",
        "location": "Koregaon Park",
    },
    {
        "name": "Priya Sharma",
        "phone": "9876543211",
        "address": "B-12, Viman Nagar, Pune",
        "location": "Viman Nagar",
    },
    {"name": "Amit Deshmukh", "phone": "9876543212", "address": "304, Kothrud, Pune", "location": "Kothrud"},
    {
        "name": "Sneha Patil",
        "phone": "9876543213",
        "address": "A-5, Hinjewadi Phase 1, Pune",
        "location": "Hinjewadi",
    },
    {"name": "Vikram Joshi", "phone": "9876543214", "address": "22, Baner Road, Pune", "location": "Baner"},
    {"name": "Anita Kulkarni", "phone": "9876543215", "address": "Flat 8, Aundh, Pune", "location": "Aundh"},
    {"name": "Rajesh Iyer", "phone": "9876543216", "address": "C-3, Wakad, Pune", "location": "Wakad"},
    {
        "name": "Meena Reddy",
        "phone": "9876543217",
        "address": "16, Magarpatta, Pune",
        "location": "Magarpatta",
    },
    {
        "name": "Suresh Nair",
        "phone": "9876543218",
        "address": "Flat 45, Hadapsar, Pune",
        "location": "Hadapsar",
    },
    {
        "name": "Kavita Ghosh",
        "phone": "9876543219",
        "address": "B-7, Kalyani Nagar, Pune",
        "location": "Kalyani Nagar",
    },
    {
        "name": "Manoj Tiwari",
        "phone": "9876543220",
        "address": "12, Shivajinagar, Pune",
        "location": "Shivajinagar",
    },
    {
        "name": "Deepa Menon",
        "phone": "9876543221",
        "address": "D-9, Pimple Saudagar, Pune",
        "location": "Pimple Saudagar",
    },
    {"name": "Sanjay Gupta", "phone": "9876543222", "address": "Flat 18, Deccan, Pune", "location": "Deccan"},
    {"name": "Pooja Bhatt", "phone": "9876543223", "address": "A-14, Bavdhan, Pune", "location": "Bavdhan"},
    {"name": "Arjun Singh", "phone": "9876543224", "address": "C-21, Warje, Pune", "location": "Warje"},
    {
        "name": "Nisha Verma",
        "phone": "9876543225",
        "address": "7, Sinhagad Road, Pune",
        "location": "Sinhagad Road",
    },
    {"name": "Kiran Rao", "phone": "9876543226", "address": "Flat 33, Camp Area, Pune", "location": "Camp"},
    {"name": "Ritu Agarwal", "phone": "9876543227", "address": "B-2, Pashan, Pune", "location": "Pashan"},
    {"name": "Nitin Deshpande", "phone": "9876543228", "address": "15, Kondhwa, Pune", "location": "Kondhwa"},
    {"name": "Swati Jain", "phone": "9876543229", "address": "E-4, Nibm Road, Pune", "location": "NIBM"},
]

PAYMENT_METHODS = [PaymentMethod.CASH, PaymentMethod.UPI, PaymentMethod.BANK_TRANSFER]


class Command(BaseCommand):
    help = "Seed demo data for Annapurna Mess"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Flush all data before seeding",
        )

    def handle(self, **options):
        self.rng = random.Random(42)

        if options["reset"]:
            self._flush()
            self.stdout.write(self.style.WARNING("All data flushed."))

        if Business.objects.filter(name=BUSINESS_NAME).exists():
            raise CommandError(f'Business "{BUSINESS_NAME}" already exists. Use --reset to flush first.')

        with transaction.atomic():
            biz = self._create_business()
            self._create_settings(biz)
            staff = self._create_staff(biz)
            customers = self._create_customers(biz)
            meals = self._get_meals(biz)
            plans = self._create_plans(biz, meals)
            self._create_subscriptions_and_data(biz, staff, customers, plans, meals)
            self._create_billing(biz)

        self._print_summary(biz, staff)

    # ── Flush ────────────────────────────────────────────────────────────

    def _flush(self):
        """Delete all application data. Order matters for FK constraints."""
        AuditLog.objects.all().delete()
        Notification.objects.all().delete()
        MealSkip.objects.all().delete()
        SubscriptionPause.objects.all().delete()
        Delivery.objects.all().delete()
        Payment.objects.all().delete()
        Subscription.objects.all().delete()
        Plan.objects.all().delete()
        Meal.objects.all().delete()
        Customer.objects.all().delete()
        BusinessSettings.objects.all().delete()
        User.objects.all().delete()
        Business.objects.all().delete()

    # ── Business + Settings ──────────────────────────────────────────────

    def _create_business(self):
        return Business.objects.create(
            name=BUSINESS_NAME,
            phone="020-25551234",
            email="contact@annapurnamess.in",
            address="123, FC Road, Deccan Gymkhana, Pune 411004",
            status="ACTIVE",
        )

    def _create_billing(self, biz):
        """Demo business is a paying customer: setup + first month, then one renewal."""
        from apps.platform.models import PaymentMethod
        from apps.platform.services import PlatformService

        sub = PlatformService.start_billing(biz)
        today = datetime.date.today()
        for days_ago in (40, 10):
            pay_day = today - datetime.timedelta(days=days_ago)
            due = PlatformService.amount_due(sub, pay_day)
            PlatformService.record_manual_payment(
                sub, amount=due.total, method=PaymentMethod.UPI, reference=f"DEMO-{days_ago}", today=pay_day
            )
            sub.refresh_from_db()

    def _create_settings(self, biz):
        return BusinessSettings.objects.create(
            business=biz,
            skip_rule=SkipRule.EXTEND,
            min_pause_days=1,
            max_pause_days=7,
            max_skip_days=3,
            delivery_start_time=datetime.time(11, 0),
            delivery_end_time=datetime.time(14, 0),
            notify_on_payment=True,
            notify_on_expiring=True,
            notify_on_delivery=False,
        )

    # ── Staff ────────────────────────────────────────────────────────────

    def _create_staff(self, biz):
        users = {}
        staff_data = [
            ("owner", "owner123", "Ramesh Kulkarni", Role.OWNER, "ramesh@annapurna.in", "9800000001"),
            ("manager", "manager123", "Priya Deshpande", Role.MANAGER, "priya@annapurna.in", "9800000002"),
            (
                "delivery1",
                "delivery123",
                "Vikram Jadhav",
                Role.DELIVERY_STAFF,
                "vikram@annapurna.in",
                "9800000003",
            ),
            (
                "kitchen1",
                "kitchen123",
                "Sunita Pawar",
                Role.KITCHEN_STAFF,
                "sunita@annapurna.in",
                "9800000004",
            ),
        ]
        for username, password, name, role, email, phone in staff_data:
            users[role] = User.objects.create_user(
                username=username,
                password=password,
                name=name,
                role=role,
                business=biz,
                email=email,
                phone=phone,
                is_active=True,
            )
        return users

    # ── Customers ────────────────────────────────────────────────────────

    def _create_customers(self, biz):
        customers = []
        for i, data in enumerate(CUSTOMER_DATA):
            status = Status.ACTIVE
            if i == 18:
                status = Status.INACTIVE
            elif i == 19:
                status = Status.BLOCKED
            cust = Customer.objects.create(
                business=biz,
                name=data["name"],
                phone=data["phone"],
                email=f"{data['name'].split()[0].lower()}@example.com",
                address=data["address"],
                location=data["location"],
                status=status,
            )
            customers.append(cust)
        return customers

    # ── Meals ────────────────────────────────────────────────────────────

    def _get_meals(self, biz):
        """Create default meals (same as bootstrap)."""
        names = ["Breakfast", "Lunch", "Dinner", "Snacks"]
        meals = {}
        for name in names:
            meals[name], _ = Meal.objects.get_or_create(business=biz, name=name)
        return meals

    # ── Plans ────────────────────────────────────────────────────────────

    def _create_plans(self, biz, meals):
        plan_defs = [
            ("Weekly Breakfast", meals["Breakfast"], 7, 7, Decimal("500.00"), True, False),
            ("Fortnightly Lunch", meals["Lunch"], 15, 15, Decimal("1200.00"), True, True),
            ("Monthly Lunch", meals["Lunch"], 30, 30, Decimal("2500.00"), True, True),
            ("Monthly Dinner", meals["Dinner"], 30, 30, Decimal("2000.00"), True, True),
            ("Monthly Full Meals", meals["Lunch"], 30, 30, Decimal("3500.00"), True, True),
        ]
        plans = {}
        for name, meal, days, total, price, skip, pause in plan_defs:
            plans[name] = Plan.objects.create(
                business=biz,
                name=name,
                meal=meal,
                duration_days=days,
                total_meals=total,
                price=price,
                skip_allowed=skip,
                pause_allowed=pause,
                is_active=True,
            )
        return plans

    # ── Subscriptions + Payments + Deliveries ────────────────────────────

    def _create_subscriptions_and_data(self, biz, staff, customers, plans, meals):
        owner = staff[Role.OWNER]
        delivery_staff = staff[Role.DELIVERY_STAFF]
        plan_list = list(plans.values())

        # Helper to pick a plan
        def pick_plan(idx=None):
            if idx is not None:
                return plan_list[idx % len(plan_list)]
            return self.rng.choice(plan_list)

        # ── 8 ACTIVE subscriptions (start 3-20 days ago, fully paid) ────
        for i in range(8):
            cust = customers[i]
            plan = pick_plan(i)
            days_ago = self.rng.randint(3, 20)
            start = TODAY - timedelta(days=days_ago)
            sub = SubscriptionService.create_subscription(
                business_id=biz.id,
                customer=cust,
                plan=plan,
                start_date=start,
            )
            method = self.rng.choice(PAYMENT_METHODS)
            PaymentService.record_payment(
                business_id=biz.id,
                subscription=sub,
                amount=plan.price,
                method=method,
                payment_date=start,
            )
            # sub is now ACTIVE with deliveries generated
            sub.refresh_from_db()
            self._process_past_deliveries(sub, delivery_staff)

        # ── 3 EXPIRING (ACTIVE but end_date within 1-3 days) ────────────
        for i in range(3):
            cust = customers[8 + i]
            plan = plans["Monthly Lunch"]
            # Start 27-29 days ago so end_date is 1-3 days from now
            days_ago = plan.duration_days - self.rng.randint(1, 3)
            start = TODAY - timedelta(days=days_ago)
            sub = SubscriptionService.create_subscription(
                business_id=biz.id,
                customer=cust,
                plan=plan,
                start_date=start,
            )
            PaymentService.record_payment(
                business_id=biz.id,
                subscription=sub,
                amount=plan.price,
                method=PaymentMethod.UPI,
                payment_date=start,
            )
            sub.refresh_from_db()
            self._process_past_deliveries(sub, delivery_staff)

        # ── 3 PENDING (1 zero payment, 2 partial) ───────────────────────
        for i in range(3):
            cust = customers[11 + i]
            plan = pick_plan(i + 2)
            sub = SubscriptionService.create_subscription(
                business_id=biz.id,
                customer=cust,
                plan=plan,
                start_date=TODAY,
            )
            if i > 0:
                # Partial payment (30-50%)
                pct = Decimal(str(self.rng.randint(30, 50))) / Decimal("100")
                partial_amount = (plan.price * pct).quantize(Decimal("0.01"))
                PaymentService.record_payment(
                    business_id=biz.id,
                    subscription=sub,
                    amount=partial_amount,
                    method=PaymentMethod.CASH,
                    payment_date=TODAY,
                )

        # ── 2 EXPIRED (start 45-60 days ago, activated, then force EXPIRED) ──
        for i in range(2):
            cust = customers[14 + i]
            plan = plans["Monthly Lunch"]
            days_ago = self.rng.randint(45, 60)
            start = TODAY - timedelta(days=days_ago)
            sub = SubscriptionService.create_subscription(
                business_id=biz.id,
                customer=cust,
                plan=plan,
                start_date=start,
            )
            PaymentService.record_payment(
                business_id=biz.id,
                subscription=sub,
                amount=plan.price,
                method=PaymentMethod.BANK_TRANSFER,
                payment_date=start,
            )
            sub.refresh_from_db()
            self._process_past_deliveries(sub, delivery_staff)
            # Force to EXPIRED (normally done by nightly sweep)
            Subscription.objects.filter(id=sub.id).update(status=SubStatus.EXPIRED)

        # ── 2 CANCELLED (1 was active then cancelled, 1 cancelled while pending)
        cust = customers[16]
        plan = plans["Monthly Dinner"]
        start = TODAY - timedelta(days=10)
        sub = SubscriptionService.create_subscription(
            business_id=biz.id,
            customer=cust,
            plan=plan,
            start_date=start,
        )
        PaymentService.record_payment(
            business_id=biz.id,
            subscription=sub,
            amount=plan.price,
            method=PaymentMethod.CASH,
            payment_date=start,
        )
        sub.refresh_from_db()
        SubscriptionService.cancel(sub)

        cust = customers[17]
        plan = plans["Weekly Breakfast"]
        sub = SubscriptionService.create_subscription(
            business_id=biz.id,
            customer=cust,
            plan=plan,
            start_date=TODAY,
        )
        SubscriptionService.cancel(sub)

        # ── 2 PAUSED (active then paused, deliveries in pause range cancelled)
        for i in range(2):
            cust = customers[8 + i]  # Reuse customers who also have expiring subs
            plan = plans["Monthly Dinner"]
            start = TODAY - timedelta(days=15)
            sub = SubscriptionService.create_subscription(
                business_id=biz.id,
                customer=cust,
                plan=plan,
                start_date=start,
            )
            PaymentService.record_payment(
                business_id=biz.id,
                subscription=sub,
                amount=plan.price,
                method=PaymentMethod.UPI,
                payment_date=start,
            )
            sub.refresh_from_db()
            self._process_past_deliveries(sub, delivery_staff)
            # Pause
            SubscriptionService.pause(sub)
            pause_start = TODAY
            pause_end = TODAY + timedelta(days=3)
            DeliveryService.pause_deliveries(
                sub,
                start_date=pause_start,
                end_date=pause_end,
                reason="Out of station",
            )

        # ── 1 RENEWED chain (expired → renew → pay → ACTIVE) ────────────
        cust = customers[14]  # Reuse an expired customer
        expired_sub = Subscription.objects.filter(
            customer=cust,
            status=SubStatus.EXPIRED,
        ).first()
        if expired_sub:
            renewed_sub = SubscriptionService.renew(expired_sub, start_date=TODAY)
            PaymentService.record_payment(
                business_id=biz.id,
                subscription=renewed_sub,
                amount=renewed_sub.total_amount,
                method=PaymentMethod.UPI,
                payment_date=TODAY,
            )
            renewed_sub.refresh_from_db()

        # ── Create 5 customer portal users ───────────────────────────────
        for i in range(5):
            cust = customers[i]
            portal_user = User.objects.create_user(
                username=f"customer{i + 1}",
                password="customer123",
                name=cust.name,
                role=Role.CUSTOMER,
                business=biz,
                email=cust.email,
                phone=cust.phone,
                is_active=True,
            )
            cust.user = portal_user
            cust.save(update_fields=["user", "updated_at"])

        # ── Audit log entries ────────────────────────────────────────────
        self._create_audit_logs(biz, owner, customers)

        # ── Extra notifications ──────────────────────────────────────────
        self._create_notifications(biz, owner)

    # ── Helpers ──────────────────────────────────────────────────────────

    def _process_past_deliveries(self, sub, delivery_staff):
        """Mark past deliveries as DELIVERED/NOT_DELIVERED/SKIPPED."""
        past_deliveries = Delivery.objects.filter(
            subscription=sub,
            delivery_date__lt=TODAY,
            status=DeliveryStatus.PENDING,
        )
        for d in past_deliveries:
            roll = self.rng.random()
            if roll < 0.82:
                d.status = DeliveryStatus.DELIVERED
                d.delivered_at = timezone.make_aware(
                    datetime.datetime.combine(d.delivery_date, datetime.time(12, 30))
                )
                d.assigned_staff = delivery_staff
            elif roll < 0.92:
                d.status = DeliveryStatus.NOT_DELIVERED
                d.notes = self.rng.choice(["Customer not home", "Wrong address", "Delivery delayed"])
                d.assigned_staff = delivery_staff
            else:
                d.status = DeliveryStatus.SKIPPED
                # Create MealSkip record
                MealSkip.objects.create(
                    business_id=sub.business_id,
                    subscription=sub,
                    customer=sub.customer,
                    delivery=d,
                    skip_date=d.delivery_date,
                    reason=self.rng.choice(["Not hungry", "Out of town", "Festival holiday"]),
                )
            d.save(update_fields=["status", "delivered_at", "assigned_staff", "notes", "updated_at"])

    def _create_audit_logs(self, biz, owner, customers):
        actions = [
            ("CREATE", "Customer", customers[0].id, f"Created customer {customers[0].name}"),
            ("CREATE", "Customer", customers[1].id, f"Created customer {customers[1].name}"),
            ("CREATE", "Plan", "plan-id", "Created Monthly Lunch plan"),
            ("CREATE", "Subscription", "sub-id", f"Subscription for {customers[0].name}"),
            ("UPDATE", "Subscription", "sub-id", f"Activated subscription for {customers[0].name}"),
            ("CREATE", "Payment", "pay-id", f"Payment received from {customers[0].name}"),
            ("UPDATE", "Delivery", "del-id", "Marked delivery as DELIVERED"),
            ("UPDATE", "Subscription", "sub-id", f"Paused subscription for {customers[8].name}"),
            ("UPDATE", "Subscription", "sub-id", f"Cancelled subscription for {customers[16].name}"),
            ("CREATE", "BusinessSettings", "settings-id", "Updated business settings"),
        ]
        for action, entity_type, entity_id, description in actions:
            AuditService.log(
                business_id=biz.id,
                user=owner,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id),
                description=description,
            )

    def _create_notifications(self, biz, owner):
        """Create some extra notifications beyond auto-generated ones."""
        NotificationService.emit_expiring_notifications(biz.id)

    # ── Summary ──────────────────────────────────────────────────────────

    def _print_summary(self, biz, staff):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"  Seed data created for '{BUSINESS_NAME}'"))
        self.stdout.write("=" * 60)

        self.stdout.write(f"\n  Business:       {biz.name} (id={biz.id})")
        self.stdout.write(f"  Customers:      {Customer.objects.filter(business=biz).count()}")
        self.stdout.write(f"  Plans:          {Plan.objects.filter(business=biz).count()}")
        self.stdout.write(f"  Subscriptions:  {Subscription.objects.filter(business=biz).count()}")
        self.stdout.write(f"  Payments:       {Payment.objects.filter(business=biz).count()}")
        self.stdout.write(f"  Deliveries:     {Delivery.objects.filter(business=biz).count()}")
        self.stdout.write(f"  MealSkips:      {MealSkip.objects.filter(business=biz).count()}")
        self.stdout.write(f"  Pauses:         {SubscriptionPause.objects.filter(business=biz).count()}")
        self.stdout.write(f"  Notifications:  {Notification.objects.filter(business=biz).count()}")
        self.stdout.write(f"  Audit logs:     {AuditLog.objects.filter(business=biz).count()}")

        # Subscription breakdown
        self.stdout.write("\n  Subscription status breakdown:")
        for st in [
            SubStatus.ACTIVE,
            SubStatus.PENDING,
            SubStatus.PAUSED,
            SubStatus.EXPIRED,
            SubStatus.CANCELLED,
        ]:
            count = Subscription.objects.filter(business=biz, status=st).count()
            self.stdout.write(f"    {st:12s}: {count}")

        self.stdout.write("\n  Login credentials:")
        self.stdout.write("  " + "-" * 50)
        self.stdout.write(f"  {'Role':<20} {'Username':<15} {'Password'}")
        self.stdout.write("  " + "-" * 50)
        self.stdout.write(f"  {'Owner':<20} {'owner':<15} owner123")
        self.stdout.write(f"  {'Manager':<20} {'manager':<15} manager123")
        self.stdout.write(f"  {'Delivery Staff':<20} {'delivery1':<15} delivery123")
        self.stdout.write(f"  {'Kitchen Staff':<20} {'kitchen1':<15} kitchen123")
        for i in range(5):
            self.stdout.write(f"  {'Customer Portal':<20} {'customer' + str(i + 1):<15} customer123")
        self.stdout.write("  " + "-" * 50)
        self.stdout.write("")
