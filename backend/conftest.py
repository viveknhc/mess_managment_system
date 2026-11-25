"""Root conftest — applies to all backend tests."""

import datetime
import zoneinfo


def pytest_configure(config):
    """Disable throttling during tests, and pin the clock (see _pin_clock)."""
    from django.conf import settings

    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}
    _pin_clock(settings.TIME_ZONE)


def _pin_clock(tz_name):
    """Run the whole session from noon (mess time) of the day it starts, clock still ticking.

    Many test modules compute ``TODAY`` once at import while the code asks for today's date
    when it runs. A run that started at 23:58 and finished at 00:02 saw two different
    "todays" and failed on dates alone. Starting at noon keeps one date for any run
    shorter than 12 hours. Runs before collection, so module-level ``TODAY`` agrees too.
    """
    import time_machine

    tz = zoneinfo.ZoneInfo(tz_name)
    noon = datetime.datetime.now(tz).replace(hour=12, minute=0, second=0, microsecond=0)
    time_machine.travel(noon, tick=True).start()
