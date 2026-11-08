"""Create or update the platform SUPER_ADMIN from environment variables.

Used by build.sh on hosts without shell access (e.g. Render free plan):

    SUPERADMIN_USERNAME=superadmin SUPERADMIN_PASSWORD=... python manage.py ensure_superadmin

No-op when SUPERADMIN_PASSWORD is unset. Re-running updates the password,
so rotating it is just changing the env var and redeploying.
"""

import os

from django.core.management.base import BaseCommand

from apps.accounts.models import User
from common.constants import Role


class Command(BaseCommand):
    help = "Create/update the SUPER_ADMIN user from SUPERADMIN_USERNAME / SUPERADMIN_PASSWORD env vars"

    def handle(self, *args, **options):
        password = os.environ.get("SUPERADMIN_PASSWORD", "")
        if not password:
            self.stdout.write("SUPERADMIN_PASSWORD not set — skipping super admin setup.")
            return
        username = os.environ.get("SUPERADMIN_USERNAME", "superadmin")

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"role": Role.SUPER_ADMIN, "business": None},
        )
        user.role = Role.SUPER_ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()
        self.stdout.write(
            self.style.SUCCESS(f"Super admin '{username}' {'created' if created else 'updated'}.")
        )
