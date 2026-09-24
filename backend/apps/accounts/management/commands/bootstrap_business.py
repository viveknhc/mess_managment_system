"""Create the first business + owner user in one transaction.

Usage:
    python manage.py bootstrap_business \
        --business-name "Rahul's Mess" \
        --owner-username admin \
        --owner-password admin123 \
        --owner-name "Rahul Kumar" \
        --owner-email admin@example.com \
        --owner-phone "9876543210"
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.businesses.models import Business
from common.constants import Role


class Command(BaseCommand):
    help = "Bootstrap the first business and owner account"

    def add_arguments(self, parser):
        parser.add_argument("--business-name", required=True)
        parser.add_argument("--owner-username", required=True)
        parser.add_argument("--owner-password", required=True)
        parser.add_argument("--owner-name", default="")
        parser.add_argument("--owner-email", default="")
        parser.add_argument("--owner-phone", default="")

    def handle(self, **options):
        if User.objects.filter(username=options["owner_username"]).exists():
            raise CommandError(f"User '{options['owner_username']}' already exists.")

        with transaction.atomic():
            business = Business.objects.create(
                name=options["business_name"],
                status="ACTIVE",
            )
            user = User.objects.create_user(
                username=options["owner_username"],
                password=options["owner_password"],
                name=options["owner_name"],
                email=options["owner_email"],
                phone=options["owner_phone"],
                role=Role.OWNER,
                business=business,
                is_active=True,
            )

        self.stdout.write(self.style.SUCCESS(f"Business '{business.name}' (id={business.id}) created."))
        self.stdout.write(self.style.SUCCESS(f"Owner '{user.username}' (id={user.id}) created."))
