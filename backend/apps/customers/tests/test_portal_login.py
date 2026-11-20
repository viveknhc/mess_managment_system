"""Customer portal login — owner/manager create, reset, disable/enable; customer can sign in."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.customization.registry import CUSTOMER_PORTAL
from apps.customization.services import FeatureService
from common.constants import Role


@pytest.fixture()
def biz_a(db):
    return Business.objects.create(name="Mess A")


@pytest.fixture()
def biz_b(db):
    return Business.objects.create(name="Mess B")


@pytest.fixture()
def cust_a(biz_a):
    return Customer.objects.create(business=biz_a, name="Alice", phone="9876500001", email="a@x.com")


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture()
def owner_a(biz_a):
    return User.objects.create_user(username="owner_a", password="pass", role=Role.OWNER, business=biz_a)


@pytest.fixture()
def client_a(owner_a):
    return _client(owner_a)


def _url(customer, suffix=""):
    return f"/api/v1/customers/{customer.id}/portal-login/{suffix}"


def _login(username, password):
    return APIClient().post("/api/v1/auth/login/", {"username": username, "password": password})


class TestCreatePortalLogin:
    def test_defaults_username_to_phone_and_generates_password(self, client_a, cust_a):
        resp = client_a.post(_url(cust_a), {}, format="json")
        assert resp.status_code == 201, resp.json()
        data = resp.json()
        assert data["username"] == "9876500001"
        assert len(data["password"]) >= 8
        cust_a.refresh_from_db()
        assert cust_a.user.role == Role.CUSTOMER
        assert cust_a.user.business_id == cust_a.business_id
        assert cust_a.user.name == "Alice"

        login = _login(data["username"], data["password"])
        assert login.status_code == 200
        access = login.json()["access"]
        portal = APIClient()
        portal.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        assert portal.get("/api/v1/portal/dashboard/").status_code == 200

    def test_custom_username_and_password(self, client_a, cust_a):
        resp = client_a.post(_url(cust_a), {"username": "alice", "password": "Tiffin#2026"}, format="json")
        assert resp.status_code == 201
        assert resp.json()["password"] == "Tiffin#2026"
        assert _login("alice", "Tiffin#2026").status_code == 200

    def test_weak_password_rejected(self, client_a, cust_a):
        resp = client_a.post(_url(cust_a), {"password": "12345678"}, format="json")
        assert resp.status_code == 400
        assert "password" in resp.json()["error"]["fields"]
        cust_a.refresh_from_db()
        assert cust_a.user is None

    def test_username_taken_rejected(self, client_a, cust_a, biz_b):
        User.objects.create_user(username="9876500001", password="x", role=Role.OWNER, business=biz_b)
        resp = client_a.post(_url(cust_a), {}, format="json")
        assert resp.status_code == 400
        assert "username" in resp.json()["error"]["fields"]

    def test_invalid_username_rejected(self, client_a, cust_a):
        resp = client_a.post(_url(cust_a), {"username": "has space"}, format="json")
        assert resp.status_code == 400

    def test_no_phone_needs_username(self, client_a, biz_a):
        c = Customer.objects.create(business=biz_a, name="NoPhone")
        resp = client_a.post(_url(c), {}, format="json")
        assert resp.status_code == 400
        assert "username" in resp.json()["error"]["fields"]

    def test_cannot_create_twice(self, client_a, cust_a):
        assert client_a.post(_url(cust_a), {}, format="json").status_code == 201
        assert client_a.post(_url(cust_a), {"username": "other"}, format="json").status_code == 400

    def test_detail_shows_login_without_password(self, client_a, cust_a):
        assert client_a.get(f"/api/v1/customers/{cust_a.id}/").json()["portal_login"] is None
        client_a.post(_url(cust_a), {}, format="json")
        info = client_a.get(f"/api/v1/customers/{cust_a.id}/").json()["portal_login"]
        assert info == {"username": "9876500001", "is_active": True}

    def test_manager_allowed(self, biz_a, cust_a):
        mgr = User.objects.create_user(username="mgr", password="p", role=Role.MANAGER, business=biz_a)
        assert _client(mgr).post(_url(cust_a), {}, format="json").status_code == 201

    @pytest.mark.parametrize("role", [Role.DELIVERY_STAFF, Role.KITCHEN_STAFF, Role.CUSTOMER])
    def test_other_roles_forbidden(self, biz_a, cust_a, role):
        u = User.objects.create_user(username=f"u_{role}", password="p", role=role, business=biz_a)
        assert _client(u).post(_url(cust_a), {}, format="json").status_code == 403

    def test_tenant_isolation_404(self, biz_b, cust_a):
        owner_b = User.objects.create_user(username="owner_b", password="p", role=Role.OWNER, business=biz_b)
        assert _client(owner_b).post(_url(cust_a), {}, format="json").status_code == 404
        cust_a.refresh_from_db()
        assert cust_a.user is None

    def test_blocked_when_portal_feature_off(self, client_a, cust_a, biz_a):
        FeatureService.set_overrides(biz_a.id, {CUSTOMER_PORTAL: False})
        assert client_a.post(_url(cust_a), {}, format="json").status_code == 403


class TestManagePortalLogin:
    @pytest.fixture()
    def created(self, client_a, cust_a):
        return client_a.post(_url(cust_a), {}, format="json").json()

    def test_reset_password_changes_it(self, client_a, cust_a, created):
        resp = client_a.post(_url(cust_a, "reset-password/"), {}, format="json")
        assert resp.status_code == 200
        new = resp.json()["password"]
        assert new != created["password"]
        assert _login(created["username"], created["password"]).status_code == 401
        assert _login(created["username"], new).status_code == 200

    def test_reset_without_login_400(self, client_a, cust_a):
        assert client_a.post(_url(cust_a, "reset-password/"), {}, format="json").status_code == 400

    def test_disable_blocks_login_and_enable_restores(self, client_a, cust_a, created):
        resp = client_a.post(_url(cust_a, "disable/"))
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False
        assert _login(created["username"], created["password"]).status_code == 401

        assert client_a.post(_url(cust_a, "enable/")).json()["is_active"] is True
        assert _login(created["username"], created["password"]).status_code == 200

    def test_soft_delete_disables_login(self, client_a, cust_a, created):
        assert client_a.delete(f"/api/v1/customers/{cust_a.id}/").status_code == 204
        cust_a.refresh_from_db()
        assert cust_a.user.is_active is False
