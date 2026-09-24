"""Auth endpoint tests (A-07)."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from common.constants import Role


@pytest.fixture()
def business(db):
    return Business.objects.create(name="Test Mess", status="ACTIVE")


@pytest.fixture()
def owner(business):
    return User.objects.create_user(
        username="owner",
        password="testpass123",
        name="Test Owner",
        role=Role.OWNER,
        business=business,
        is_active=True,
    )


@pytest.fixture()
def inactive_user(business):
    return User.objects.create_user(
        username="inactive",
        password="testpass123",
        role=Role.OWNER,
        business=business,
        is_active=False,
    )


@pytest.fixture()
def api():
    return APIClient()


@pytest.mark.django_db
class TestLogin:
    def test_login_success(self, api, owner):
        resp = api.post("/api/v1/auth/login/", {"username": "owner", "password": "testpass123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access" in data
        assert "refresh" in data
        assert data["user"]["role"] == Role.OWNER
        assert data["user"]["business_name"] == "Test Mess"

    def test_login_bad_credentials(self, api, owner):
        resp = api.post("/api/v1/auth/login/", {"username": "owner", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_inactive_user(self, api, inactive_user):
        resp = api.post("/api/v1/auth/login/", {"username": "inactive", "password": "testpass123"})
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, api, db):
        resp = api.post("/api/v1/auth/login/", {"username": "nobody", "password": "x"})
        assert resp.status_code == 401


@pytest.mark.django_db
class TestRefresh:
    def test_refresh_returns_new_access(self, api, owner):
        login = api.post("/api/v1/auth/login/", {"username": "owner", "password": "testpass123"})
        refresh_token = login.json()["refresh"]

        resp = api.post("/api/v1/auth/refresh/", {"refresh": refresh_token})
        assert resp.status_code == 200
        assert "access" in resp.json()

    def test_refresh_with_invalid_token(self, api, db):
        resp = api.post("/api/v1/auth/refresh/", {"refresh": "invalid-token"})
        assert resp.status_code == 401


@pytest.mark.django_db
class TestLogout:
    def test_logout_blacklists_refresh(self, api, owner):
        login = api.post("/api/v1/auth/login/", {"username": "owner", "password": "testpass123"})
        tokens = login.json()
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        resp = api.post("/api/v1/auth/logout/", {"refresh": tokens["refresh"]})
        assert resp.status_code == 200

        # Refresh token should now be blacklisted
        resp = api.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]})
        assert resp.status_code == 401

    def test_logout_requires_auth(self, api, db):
        resp = api.post("/api/v1/auth/logout/", {"refresh": "x"})
        assert resp.status_code == 401

    def test_logout_requires_refresh_token(self, api, owner):
        login = api.post("/api/v1/auth/login/", {"username": "owner", "password": "testpass123"})
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")
        resp = api.post("/api/v1/auth/logout/", {})
        assert resp.status_code == 400


@pytest.mark.django_db
class TestMe:
    def test_me_returns_user_profile(self, api, owner):
        login = api.post("/api/v1/auth/login/", {"username": "owner", "password": "testpass123"})
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")

        resp = api.get("/api/v1/auth/me/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "owner"
        assert data["role"] == Role.OWNER
        assert data["business_name"] == "Test Mess"

    def test_me_requires_auth(self, api, db):
        resp = api.get("/api/v1/auth/me/")
        assert resp.status_code == 401

    def test_me_different_roles(self, api, business):
        for role in [Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF, Role.CUSTOMER]:
            user = User.objects.create_user(
                username=f"user_{role}", password="pass", role=role, business=business
            )
            login = api.post("/api/v1/auth/login/", {"username": f"user_{role}", "password": "pass"})
            api.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")
            resp = api.get("/api/v1/auth/me/")
            assert resp.json()["role"] == role
            user.delete()
