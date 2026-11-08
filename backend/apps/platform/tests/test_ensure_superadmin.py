"""ensure_superadmin management command (used by build.sh on deploy)."""

import pytest
from django.core.management import call_command

from apps.accounts.models import User
from common.constants import Role


@pytest.mark.django_db
def test_skips_without_password(monkeypatch):
    monkeypatch.delenv("SUPERADMIN_PASSWORD", raising=False)
    call_command("ensure_superadmin")
    assert not User.objects.filter(role=Role.SUPER_ADMIN).exists()


@pytest.mark.django_db
def test_creates_super_admin(monkeypatch):
    monkeypatch.setenv("SUPERADMIN_USERNAME", "platform")
    monkeypatch.setenv("SUPERADMIN_PASSWORD", "first-Pass-123")
    call_command("ensure_superadmin")
    user = User.objects.get(username="platform")
    assert user.role == Role.SUPER_ADMIN
    assert user.business is None
    assert user.is_staff and user.is_superuser
    assert user.check_password("first-Pass-123")


@pytest.mark.django_db
def test_rerun_updates_password_without_duplicating(monkeypatch):
    monkeypatch.setenv("SUPERADMIN_PASSWORD", "first-Pass-123")
    call_command("ensure_superadmin")
    monkeypatch.setenv("SUPERADMIN_PASSWORD", "rotated-Pass-456")
    call_command("ensure_superadmin")
    assert User.objects.filter(username="superadmin").count() == 1
    assert User.objects.get(username="superadmin").check_password("rotated-Pass-456")
