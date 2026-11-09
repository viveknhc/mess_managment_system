"""Run the nightly jobs (settings.DAILY_JOBS) in-process, without Celery.

For hosts with no Celery worker/beat: call it once a day from a cron, e.g. the
"Daily jobs" GitHub Actions workflow. Safe to re-run — every job is idempotent.
"""

import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the nightly jobs (billing checks, subscription expiry, deliveries, expiry alerts)."

    def handle(self, *args, **options):
        failed = []
        for path in settings.DAILY_JOBS:
            try:
                result = import_string(path)()  # calling a Celery task runs it synchronously
            except Exception:
                logger.exception("Daily job %s failed", path)
                failed.append(path)
                self.stderr.write(self.style.ERROR(f"FAILED  {path}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"OK      {path}") + (f"  {result}" if result else ""))
        if failed:
            raise CommandError(f"{len(failed)} job(s) failed: {', '.join(failed)}")
