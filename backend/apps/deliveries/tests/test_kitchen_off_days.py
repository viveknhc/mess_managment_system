"""Weekly kitchen off days (e.g. Sunday closed): no deliveries on closed days, meals are
kept and the end date moves later — on create, skip, pause, and when the owner changes
the setting for existing subscriptions. Plus validation and tenant isolation."""

import datetime
from datetime import timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.customization.registry import SKIP
from apps.customization.services import PolicyService
from apps.deliveries.models import Delivery, DeliveryStatus
from apps.deliveries.services import DeliveryService
from apps.meals.models import Meal
from apps.plans.models import Plan
from apps.settings_app.models import BusinessSettings
from apps.settings_app.services import KitchenCalendar
from apps.subscriptions.services import SubscriptionService
from common.constants import Role, SubStatus

SUNDAY = 6
T = datetime.date.today()
MON = T + timedelta(days=7 - T.weekday())  # next Monday, always in the future


def day(n):
    return MON + timedelta(days=n)


def close_on(biz, *weekdays):
    BusinessSettings.objects.update_or_create(business=biz, defaults={"weekly_off_days": list(weekdays)})


def live_dates(sub):
    return sorted(
        Delivery.objects.filter(subscription=sub)
        .exclude(status=DeliveryStatus.CANCELLED)
        .values_list("delivery_date", flat=True)
    )


@pytest.fixture()
def biz(db):
    return Business.objects.create(name="Sunday Off Mess")


@pytest.fixture()
def other_biz(db):
    return Business.objects.create(name="Open Daily Mess")


@pytest.fixture()
def owner(biz):
    return User.objects.create_user(username="owner", password="pass", role=Role.OWNER, business=biz)


def make_plan(business, *, days, meals, price="0.00"):
    meal = Meal.objects.create(business=business, name=f"Lunch {days}/{meals}")
    return Plan.objects.create(
        business=business,
        name=f"Plan {days}/{meals}",
        meal=meal,
        duration_days=days,
        total_meals=meals,
        price=Decimal(price),
        skip_allowed=True,
        pause_allowed=True,
    )


def subscribe(business, plan, start=MON, phone="9000000001"):
    customer = Customer.objects.create(business=business, name="Asha", phone=phone)
    return SubscriptionService.create_subscription(
        business_id=business.id, customer=customer, plan=plan, start_date=start
    )


class TestKitchenCalendar:
    def test_nth_open_day_skips_closed_days(self):
        cal = KitchenCalendar([SUNDAY])
        assert cal.nth_open_day(MON, 1) == MON
        assert cal.nth_open_day(MON, 6) == day(5)  # Saturday
        assert cal.nth_open_day(MON, 7) == day(7)  # next Monday, Sunday skipped

    def test_add_open_days_skips_closed_days(self):
        cal = KitchenCalendar([SUNDAY])
        assert cal.add_open_days(day(5), 1) == day(7)  # Saturday + 1 → Monday
        assert cal.add_open_days(day(5), 0) == day(5)

    def test_closed_every_day_is_ignored(self):
        assert KitchenCalendar(range(7)).is_open(MON)

    def test_plan_end_date_never_shortens_the_plan(self):
        cal = KitchenCalendar([SUNDAY])
        assert cal.plan_end_date(MON, 30, 26) == MON + timedelta(days=30)
        assert cal.plan_end_date(MON, 30, 30) > MON + timedelta(days=30)


@pytest.mark.django_db
class TestSchedule:
    def test_no_off_days_behaves_as_before(self, biz):
        sub = subscribe(biz, make_plan(biz, days=7, meals=7))
        assert sub.end_date == MON + timedelta(days=7)
        assert live_dates(sub) == [day(i) for i in range(7)]

    def test_no_delivery_on_sunday_and_all_meals_kept(self, biz):
        close_on(biz, SUNDAY)
        sub = subscribe(biz, make_plan(biz, days=7, meals=7))
        dates = live_dates(sub)
        assert len(dates) == 7
        assert all(d.weekday() != SUNDAY for d in dates)
        assert sub.end_date == day(7) == dates[-1]
        assert sub.status == SubStatus.ACTIVE

    def test_plan_already_sized_for_sunday_off(self, biz):
        close_on(biz, SUNDAY)
        sub = subscribe(biz, make_plan(biz, days=30, meals=26))
        dates = live_dates(sub)
        assert len(dates) == 26
        assert all(d.weekday() != SUNDAY for d in dates)
        assert sub.end_date == MON + timedelta(days=30)

    def test_paid_plan_gets_stretched_end_date_while_pending(self, biz):
        close_on(biz, SUNDAY)
        sub = subscribe(biz, make_plan(biz, days=7, meals=7, price="700.00"))
        assert sub.status == SubStatus.PENDING
        assert sub.end_date == day(7)

    def test_two_closed_days(self, biz):
        close_on(biz, 5, SUNDAY)  # Saturday and Sunday
        sub = subscribe(biz, make_plan(biz, days=7, meals=7))
        dates = live_dates(sub)
        assert len(dates) == 7
        assert all(d.weekday() < 5 for d in dates)


@pytest.mark.django_db
class TestSkipAndPause:
    def test_skip_extension_lands_on_open_day(self, biz):
        close_on(biz, SUNDAY)
        PolicyService.set_policy(biz.id, SKIP, "EXTEND")
        sub = subscribe(biz, make_plan(biz, days=6, meals=6))  # Mon–Sat, end Sunday
        assert live_dates(sub) == [day(i) for i in range(6)]

        DeliveryService.skip_meal(Delivery.objects.get(subscription=sub, delivery_date=day(2)))
        sub.refresh_from_db()
        dates = live_dates(sub)
        assert len([d for d in dates if d != day(2)]) == 6
        assert day(6) not in dates  # not the closed Sunday
        assert day(7) in dates and sub.end_date == day(7)

    def test_pause_extension_counts_open_days_only(self, biz):
        close_on(biz, SUNDAY)
        sub = subscribe(biz, make_plan(biz, days=12, meals=12))
        SubscriptionService.pause(sub, start_date=day(1), end_date=day(2), today=T)
        SubscriptionService.process_pause_windows(today=day(3))
        sub.refresh_from_db()

        served = [d for d in live_dates(sub) if not (day(1) <= d <= day(2))]  # restored + replacement meals
        assert len(served) == 12
        assert all(d.weekday() != SUNDAY for d in served)
        assert sub.end_date == served[-1]


@pytest.mark.django_db
class TestOwnerChangesClosedDays:
    URL = "/api/v1/settings/"

    def client_for(self, user):
        c = APIClient()
        c.force_authenticate(user)
        return c

    def test_existing_subscription_moves_sunday_meals_to_the_end(self, biz, owner):
        sub = subscribe(biz, make_plan(biz, days=14, meals=14))
        assert any(d.weekday() == SUNDAY for d in live_dates(sub))

        resp = self.client_for(owner).put(self.URL, {"weekly_off_days": [SUNDAY]}, format="json")
        assert resp.status_code == 200
        assert resp.data["weekly_off_days"] == [SUNDAY]

        sub.refresh_from_db()
        dates = live_dates(sub)
        assert len(dates) == 14
        assert all(d.weekday() != SUNDAY for d in dates)
        assert sub.end_date == dates[-1] > MON + timedelta(days=14)

    def test_past_and_delivered_rows_are_untouched(self, biz, owner):
        start = T - timedelta(days=T.weekday() + 7)  # Monday a week+ ago
        sub = subscribe(biz, make_plan(biz, days=30, meals=30), start=start)
        last_sunday = start + timedelta(days=6)
        Delivery.objects.filter(subscription=sub, delivery_date=last_sunday).update(
            status=DeliveryStatus.DELIVERED
        )

        self.client_for(owner).put(self.URL, {"weekly_off_days": [SUNDAY]}, format="json")

        assert Delivery.objects.get(subscription=sub, delivery_date=last_sunday).status == (
            DeliveryStatus.DELIVERED
        )
        future = [d for d in live_dates(sub) if d >= T]
        assert all(d.weekday() != SUNDAY for d in future)
        assert len(live_dates(sub)) == 30

    def test_pending_subscription_end_date_is_refitted(self, biz, owner):
        sub = subscribe(biz, make_plan(biz, days=7, meals=7, price="700.00"))
        assert sub.end_date == day(7)
        self.client_for(owner).put(self.URL, {"weekly_off_days": [5, SUNDAY]}, format="json")
        sub.refresh_from_db()
        assert sub.end_date == day(8)  # Mon–Fri + Mon, Tue

    def test_unchanged_setting_does_nothing(self, biz, owner):
        close_on(biz, SUNDAY)
        sub = subscribe(biz, make_plan(biz, days=7, meals=7))
        before = live_dates(sub)
        self.client_for(owner).put(
            self.URL, {"weekly_off_days": [SUNDAY], "max_pause_days": 9}, format="json"
        )
        assert live_dates(sub) == before

    def test_cannot_close_every_day(self, owner):
        resp = self.client_for(owner).put(self.URL, {"weekly_off_days": list(range(7))}, format="json")
        assert resp.status_code == 400

    def test_bad_weekday_rejected_and_duplicates_collapsed(self, owner):
        c = self.client_for(owner)
        assert c.put(self.URL, {"weekly_off_days": [7]}, format="json").status_code == 400
        resp = c.put(self.URL, {"weekly_off_days": [6, 6, 0]}, format="json")
        assert resp.data["weekly_off_days"] == [0, 6]

    def test_manager_cannot_change(self, biz):
        manager = User.objects.create_user(username="mgr", password="pass", role=Role.MANAGER, business=biz)
        resp = self.client_for(manager).put(self.URL, {"weekly_off_days": [SUNDAY]}, format="json")
        assert resp.status_code == 403

    def test_other_business_is_not_affected(self, biz, other_biz, owner):
        theirs = subscribe(other_biz, make_plan(other_biz, days=14, meals=14), phone="9000000002")
        before = live_dates(theirs)
        self.client_for(owner).put(self.URL, {"weekly_off_days": [SUNDAY]}, format="json")
        assert live_dates(theirs) == before
        assert any(d.weekday() == SUNDAY for d in before)


@pytest.mark.django_db
class TestWiring:
    def test_pause_on_closed_days_only_is_rejected(self, biz):
        from apps.subscriptions.services import PauseValidationError

        close_on(biz, SUNDAY)
        sub = subscribe(biz, make_plan(biz, days=14, meals=14))
        with pytest.raises(PauseValidationError, match="closed"):
            SubscriptionService.pause(sub, start_date=day(6), end_date=day(6), today=T)
        # a window that includes an open day is fine
        SubscriptionService.pause(sub, start_date=day(6), end_date=day(7), today=T)

    def test_change_is_audited(self, biz, owner):
        from apps.audit.models import AuditLog

        subscribe(biz, make_plan(biz, days=14, meals=14))
        c = APIClient()
        c.force_authenticate(owner)
        c.put("/api/v1/settings/", {"weekly_off_days": [SUNDAY]}, format="json")
        log = AuditLog.objects.get(business=biz, entity_type="BusinessSettings")
        assert log.user == owner
        assert "Sun" in log.description and "1 subscription(s) rescheduled" in log.description

    def test_platform_mess_details_shows_closed_days(self, biz):
        from apps.platform.selectors import _settings

        close_on(biz, SUNDAY)
        assert _settings(biz)["weekly_off_days"] == [SUNDAY]


@pytest.mark.django_db
class TestClosedDaysForEveryRole:
    URL = "/api/v1/auth/me/"

    @pytest.mark.parametrize(
        "role", [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF, Role.CUSTOMER]
    )
    def test_me_includes_closed_days(self, biz, role):
        close_on(biz, 5, SUNDAY)
        user = User.objects.create_user(username=f"u_{role}", password="pass", role=role, business=biz)
        c = APIClient()
        c.force_authenticate(user)
        assert c.get(self.URL).data["kitchen_off_days"] == [5, SUNDAY]

    def test_open_every_day_and_no_settings_row(self, biz, owner):
        c = APIClient()
        c.force_authenticate(owner)
        assert c.get(self.URL).data["kitchen_off_days"] == []
