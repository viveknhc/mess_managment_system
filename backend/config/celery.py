"""Celery application (arch. §12). Run as: celery -A config worker / -A config beat."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("mess_management")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
