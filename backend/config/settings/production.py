"""Production settings — fail fast on missing secrets, harden security.

Deployed on Render (see render.yaml + build.sh) with Postgres on Neon; the
React frontend is hosted separately (Vercel) and calls this API cross-origin.
"""

import logging
import os

from .base import *  # noqa: F401,F403


def _csv(name):
    """Comma-separated env var → list, ignoring blanks and trailing slashes."""
    return [v.strip().rstrip("/") for v in os.environ.get(name, "").split(",") if v.strip()]


DEBUG = False
SECRET_KEY = os.environ["SECRET_KEY"]  # no default in production

ALLOWED_HOSTS = _csv("ALLOWED_HOSTS")
# Render injects the service's public hostname (e.g. mess-api.onrender.com)
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])

# Frontend origin(s), e.g. https://mess-manager.vercel.app
CORS_ALLOWED_ORIGINS = _csv("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = _csv("CSRF_TRUSTED_ORIGINS") or CORS_ALLOWED_ORIGINS

# Keep DB connections open between requests (Neon/Postgres)
DATABASES["default"]["CONN_MAX_AGE"] = 60  # noqa: F405
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True  # noqa: F405

# Static files (Django admin CSS/JS) served by WhiteNoise — no separate web server needed
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405 — right after SecurityMiddleware
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Email: explicit EMAIL_BACKEND wins; else SMTP when EMAIL_HOST is configured,
# otherwise fall back to console (emails only appear in logs) with a warning.
if not os.environ.get("EMAIL_BACKEND"):
    if EMAIL_HOST:  # noqa: F405
        EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    else:
        EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
        logging.getLogger(__name__).warning(
            "EMAIL_HOST is not set — using console email backend; expiry alert emails will not be delivered."
        )

# Log to stdout so errors show up in the host's log viewer
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
