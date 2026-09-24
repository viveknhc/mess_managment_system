"""Root conftest — applies to all backend tests."""


def pytest_configure(config):
    """Disable throttling during tests."""
    from django.conf import settings

    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}
