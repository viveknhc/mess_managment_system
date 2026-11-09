"""
Django settings for the Mess Management System.

Base settings shared by all environments (arch. §6.5). Environment-specific
modules (local.py, production.py) import * from here and override.
"""

from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "insecure-dev-only-secret-key"),
    ALLOWED_HOSTS=(list, []),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    # local apps (mod. plan §20)
    "apps.accounts",
    "apps.businesses",
    "apps.customers",
    "apps.meals",
    "apps.plans",
    "apps.subscriptions",
    "apps.payments",
    "apps.deliveries",
    "apps.notifications",
    "apps.settings_app",
    "apps.audit",
    "apps.platform",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database — DATABASE_URL decides (postgres in docker/CI; sqlite fallback bare-local)
DATABASES = {
    "default": env.db_url_config(env.str("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"))
}

# Custom user (poc.md §7.2) — must be set before the first migration
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# i18n / tz
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# Static & media
STATIC_URL = "static/"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF (arch. §8) ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("common.authentication.TenantJWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "common.filters.StableOrderingFilter",
    ),
    "EXCEPTION_HANDLER": "common.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "auth": "5/min",
        "writes": "60/min",
        "reads": "120/min",
    },
}

# --- JWT (arch. §8.2; system_design.md D7) ---
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# --- Celery (arch. §12) ---
CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_TASK_ACKS_LATE = True
CELERY_TIMEZONE = TIME_ZONE

# Nightly jobs, in run order. Celery beat runs them on Celery hosts; elsewhere
# (e.g. Render free tier) `python manage.py run_daily_jobs` runs them from a cron.
DAILY_JOBS = [
    "apps.platform.tasks.run_billing_checks",  # overdue → past due → suspended
    "apps.deliveries.tasks.expire_subscriptions_task",  # ACTIVE past end_date → EXPIRED
    "apps.subscriptions.tasks.process_pause_windows_task",  # start/end pause windows
    "apps.deliveries.tasks.generate_next_day_deliveries_task",
    "apps.notifications.tasks.send_expiring_notifications_task",  # expiry alerts
]
CELERY_BEAT_SCHEDULE = {
    task.rsplit(".", 1)[1]: {"task": task, "schedule": crontab(hour=0, minute=10 + 5 * i)}
    for i, task in enumerate(DAILY_JOBS)
}

# --- Razorpay (SaaS billing) ---
RAZORPAY_KEY_ID = env.str("RAZORPAY_KEY_ID", default="")
RAZORPAY_KEY_SECRET = env.str("RAZORPAY_KEY_SECRET", default="")
RAZORPAY_WEBHOOK_SECRET = env.str("RAZORPAY_WEBHOOK_SECRET", default="")

# --- Email (expiry alerts; see apps/notifications) ---
# Default: console backend (prints emails). production.py switches to SMTP when
# EMAIL_HOST is set. Tests get Django's locmem backend automatically.
EMAIL_BACKEND = env.str("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env.str("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="MessDeck <noreply@localhost>")
