"""Business API + tenant isolation tests (B-02, B-03).

Covers:
- Owner can read and update their own business
- Non-owner roles can read but not update
- User of Business B gets 404 on Business A (TenantScopedViewSet isolation)
- IsSameBusiness object-level check
- Unauthenticated access is rejected
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from common.constants import Role

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture()
def biz_a(db):
    return Business.objects.create(name="Mess A", phone="1111111111")


@pytest.fixture()
def biz_b(db):
    return Business.objects.create(name="Mess B", phone="2222222222")


@pytest.fixture()
def owner_a(biz_a):
    return User.objects.create_user(username="owner_a", password="pass", role=Role.OWNER, business=biz_a)


@pytest.fixture()
def owner_b(biz_b):
    return User.objects.create_user(username="owner_b", password="pass", role=Role.OWNER, business=biz_b)


@pytest.fixture()
def manager_a(biz_a):
    return User.objects.create_user(username="manager_a", password="pass", role=Role.MANAGER, business=biz_a)


@pytest.fixture()
def staff_a(biz_a):
    return User.objects.create_user(
        username="staff_a", password="pass", role=Role.DELIVERY_STAFF, business=biz_a
    )


@pytest.fixture()
def customer_a(biz_a):
    return User.objects.create_user(
        username="customer_a", password="pass", role=Role.CUSTOMER, business=biz_a
    )


def auth_client(user):
    """Return an APIClient authenticated as the given user."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ── Business CRUD ─────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestBusinessList:
    def test_owner_sees_own_business(self, owner_a, biz_a):
        resp = auth_client(owner_a).get("/api/v1/business/")
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["name"] == "Mess A"

    def test_manager_sees_own_business(self, manager_a, biz_a):
        resp = auth_client(manager_a).get("/api/v1/business/")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_staff_sees_own_business(self, staff_a, biz_a):
        resp = auth_client(staff_a).get("/api/v1/business/")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_customer_sees_own_business(self, customer_a, biz_a):
        resp = auth_client(customer_a).get("/api/v1/business/")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

    def test_unauthenticated_rejected(self, biz_a):
        resp = APIClient().get("/api/v1/business/")
        assert resp.status_code == 401


@pytest.mark.django_db
class TestBusinessRetrieve:
    def test_owner_retrieves_own(self, owner_a, biz_a):
        resp = auth_client(owner_a).get(f"/api/v1/business/{biz_a.id}/")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Mess A"

    def test_read_only_fields_present(self, owner_a, biz_a):
        resp = auth_client(owner_a).get(f"/api/v1/business/{biz_a.id}/")
        data = resp.json()
        assert "id" in data
        assert "status" in data
        assert "created_at" in data
        assert "updated_at" in data


@pytest.mark.django_db
class TestBusinessUpdate:
    def test_owner_can_update(self, owner_a, biz_a):
        resp = auth_client(owner_a).patch(
            f"/api/v1/business/{biz_a.id}/",
            {"name": "Updated Mess A"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Mess A"

    def test_owner_full_update(self, owner_a, biz_a):
        resp = auth_client(owner_a).put(
            f"/api/v1/business/{biz_a.id}/",
            {
                "name": "Full Update",
                "phone": "9999999999",
                "email": "new@example.com",
                "address": "123 Street",
            },
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Full Update"

    def test_manager_cannot_update(self, manager_a, biz_a):
        resp = auth_client(manager_a).patch(
            f"/api/v1/business/{biz_a.id}/",
            {"name": "Hacked"},
            format="json",
        )
        assert resp.status_code == 403

    def test_staff_cannot_update(self, staff_a, biz_a):
        resp = auth_client(staff_a).patch(
            f"/api/v1/business/{biz_a.id}/",
            {"name": "Hacked"},
            format="json",
        )
        assert resp.status_code == 403

    def test_customer_cannot_update(self, customer_a, biz_a):
        resp = auth_client(customer_a).patch(
            f"/api/v1/business/{biz_a.id}/",
            {"name": "Hacked"},
            format="json",
        )
        assert resp.status_code == 403

    def test_status_not_writable(self, owner_a, biz_a):
        """Owner cannot change business status via the API."""
        auth_client(owner_a).patch(
            f"/api/v1/business/{biz_a.id}/",
            {"status": "SUSPENDED"},
            format="json",
        )
        biz_a.refresh_from_db()
        assert biz_a.status == "ACTIVE"

    def test_create_disabled(self, owner_a):
        resp = auth_client(owner_a).post(
            "/api/v1/business/",
            {"name": "New Mess"},
            format="json",
        )
        # RoleBasedPermission blocks unmapped actions before method check
        assert resp.status_code in (403, 405)

    def test_delete_disabled(self, owner_a, biz_a):
        resp = auth_client(owner_a).delete(f"/api/v1/business/{biz_a.id}/")
        assert resp.status_code in (403, 405)


# ── Tenant isolation (B-03) ──────────────────────────────────────────────


@pytest.mark.django_db
class TestTenantIsolation:
    """User of Business B must get 404 (not 403) on Business A objects."""

    def test_owner_b_cannot_list_biz_a(self, owner_b, biz_a):
        """List returns only own business — Business A not visible to B."""
        resp = auth_client(owner_b).get("/api/v1/business/")
        results = resp.json()["results"]
        ids = [r["id"] for r in results]
        assert str(biz_a.id) not in ids

    def test_owner_b_gets_404_on_biz_a_retrieve(self, owner_b, biz_a):
        resp = auth_client(owner_b).get(f"/api/v1/business/{biz_a.id}/")
        assert resp.status_code == 404

    def test_owner_b_gets_404_on_biz_a_update(self, owner_b, biz_a):
        resp = auth_client(owner_b).patch(
            f"/api/v1/business/{biz_a.id}/",
            {"name": "Stolen"},
            format="json",
        )
        assert resp.status_code == 404
        biz_a.refresh_from_db()
        assert biz_a.name == "Mess A"

    def test_owner_a_gets_404_on_biz_b(self, owner_a, biz_b):
        resp = auth_client(owner_a).get(f"/api/v1/business/{biz_b.id}/")
        assert resp.status_code == 404

    def test_staff_b_cannot_see_biz_a(self, biz_a, biz_b):
        staff_b = User.objects.create_user(
            username="staff_b", password="pass", role=Role.DELIVERY_STAFF, business=biz_b
        )
        resp = auth_client(staff_b).get(f"/api/v1/business/{biz_a.id}/")
        assert resp.status_code == 404

    def test_customer_b_cannot_see_biz_a(self, biz_a, biz_b):
        cust_b = User.objects.create_user(
            username="cust_b", password="pass", role=Role.CUSTOMER, business=biz_b
        )
        resp = auth_client(cust_b).get(f"/api/v1/business/{biz_a.id}/")
        assert resp.status_code == 404

    def test_both_owners_see_only_own(self, owner_a, owner_b, biz_a, biz_b):
        """Each owner sees exactly 1 business — their own."""
        resp_a = auth_client(owner_a).get("/api/v1/business/")
        resp_b = auth_client(owner_b).get("/api/v1/business/")

        results_a = resp_a.json()["results"]
        results_b = resp_b.json()["results"]

        assert len(results_a) == 1
        assert len(results_b) == 1
        assert results_a[0]["id"] == str(biz_a.id)
        assert results_b[0]["id"] == str(biz_b.id)
