"""Flush all data and re-seed demo data (SD-02).

Usage:
    python manage.py reset_data         # Interactive confirmation
    python manage.py reset_data --yes   # Non-interactive
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Flush all data and re-seed demo data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, **options):
        if not options["yes"]:
            confirm = input("This will DELETE all data and re-seed. Continue? [y/N] ")
            if confirm.lower() != "y":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        call_command("seed_data", "--reset")
        self.stdout.write(self.style.SUCCESS("Reset complete."))
