"""Kitchen calendar: which days a mess cooks. Read by deliveries and subscriptions."""

import datetime

from apps.settings_app.models import BusinessSettings

ONE_DAY = datetime.timedelta(days=1)


class KitchenCalendar:
    """Open/closed days of one mess. Closed days never get deliveries."""

    def __init__(self, weekly_off_days=()):
        off = frozenset(weekly_off_days or ())
        self.weekly_off_days = off if len(off) < 7 else frozenset()  # never closed every day

    @classmethod
    def for_business(cls, business_id):
        off = (
            BusinessSettings.objects.filter(business_id=business_id)
            .values_list("weekly_off_days", flat=True)
            .first()
        )
        return cls(off)

    def is_open(self, day):
        return day.weekday() not in self.weekly_off_days

    def nth_open_day(self, start, n):
        """The n-th open day on or after ``start`` (n >= 1)."""
        day, count = start, 0
        while True:
            if self.is_open(day):
                count += 1
                if count >= n:
                    return day
            day += ONE_DAY

    def add_open_days(self, day, n):
        """``day`` moved forward by ``n`` open days (n=0 → unchanged)."""
        for _ in range(n):
            day += ONE_DAY
            while not self.is_open(day):
                day += ONE_DAY
        return day

    def plan_end_date(self, start, duration_days, total_meals):
        """End date for a new subscription: the plan's length, stretched if the kitchen's
        closed days leave too few open days for all its meals."""
        return max(start + datetime.timedelta(days=duration_days), self.nth_open_day(start, total_meals))
