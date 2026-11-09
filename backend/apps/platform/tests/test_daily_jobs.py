"""run_daily_jobs: every scheduled job runs, failures don't stop the rest, beat and command share one list."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.businesses.models import Business
from apps.platform.models import SaasSubscription
from apps.platform.services import GRACE_DAYS, PlatformService
from common.constants import Status

CALLS = []


def ok_job():
    CALLS.append("ok")


def broken_job():
    raise RuntimeError("boom")


def test_every_daily_job_is_on_the_beat_schedule():
    scheduled = {entry["task"] for entry in settings.CELERY_BEAT_SCHEDULE.values()}
    assert scheduled == set(settings.DAILY_JOBS)


def test_every_daily_job_imports():
    from django.utils.module_loading import import_string

    for path in settings.DAILY_JOBS:
        assert callable(import_string(path))


@pytest.mark.django_db
def test_run_daily_jobs_runs_billing_checks():
    biz = Business.objects.create(name="Unpaid Mess")
    sub = PlatformService.start_billing(biz)
    SaasSubscription.objects.filter(pk=sub.pk).update(
        created_at=timezone.now() - timedelta(days=GRACE_DAYS + 1)
    )
    call_command("run_daily_jobs")
    biz.refresh_from_db()
    assert biz.status == Status.SUSPENDED


def test_failing_job_does_not_stop_the_others(settings):
    CALLS.clear()
    here = __name__
    settings.DAILY_JOBS = [f"{here}.broken_job", f"{here}.ok_job"]
    with pytest.raises(CommandError, match="1 job"):
        call_command("run_daily_jobs")
    assert CALLS == ["ok"]
