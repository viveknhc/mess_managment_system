"""Settings tests (ST-02)."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from common.constants import Role


@pytest.fixture()
def biz_a(db):
    return Business.objects.create(name="Mess A")


@pytest.fixture()
def owner_a(biz_a):
    return User.objects.create_user(username="owner_a", password="pass", role=Role.OWNER, business=biz_a)


@pytest.fixture()
def manager_a(biz_a):
    return User.objects.create_user(username="manager_a", password="pass", role=Role.MANAGER, business=biz_a)


@pytest.fixture()
def delivery_a(biz_a):
    return User.objects.create_user(
        username="delivery_a", password="pass", role=Role.DELIVERY_STAFF, business=biz_a
    )


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


URL = "/api/v1/settings/"


@pytest.mark.django_db
class TestBusinessSettings:
    def test_owner_can_read(self, owner_a):
        resp = auth_client(owner_a).get(URL)
        assert resp.status_code == 200
        assert "skip_rule" in resp.json()
        assert resp.json()["skip_rule"] == "NONE"

    def test_auto_creates_on_first_read(self, owner_a):
        resp = auth_client(owner_a).get(URL)
        assert resp.status_code == 200

    def test_owner_can_update(self, owner_a):
        resp = auth_client(owner_a).put(URL, {"skip_rule": "EXTEND", "max_skip_days": 5}, format="json")
        assert resp.status_code == 200
        assert resp.json()["skip_rule"] == "EXTEND"
        assert resp.json()["max_skip_days"] == 5

    def test_manager_can_read(self, manager_a):
        resp = auth_client(manager_a).get(URL)
        assert resp.status_code == 200

    def test_manager_cannot_update(self, manager_a):
        resp = auth_client(manager_a).put(URL, {"skip_rule": "EXTEND"}, format="json")
        assert resp.status_code == 403

    def test_delivery_staff_denied(self, delivery_a):
        resp = auth_client(delivery_a).get(URL)
        assert resp.status_code == 403

    def test_unauthenticated_denied(self, db):
        resp = APIClient().get(URL)
        assert resp.status_code == 401
