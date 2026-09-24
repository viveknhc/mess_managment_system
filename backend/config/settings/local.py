"""Local development settings (bare metal + pytest).

Bare local runs fall back to sqlite (see base.py); docker-compose and CI
override DATABASE_URL with Postgres.
"""

from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "django", "testserver"]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Disable throttling in tests/dev
REST_FRAMEWORK_THROTTLE_OVERRIDE = {}
import sys  # noqa: E402

if "pytest" in sys.modules or "test" in sys.argv:
    REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}  # noqa: F405
