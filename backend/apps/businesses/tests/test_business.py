"""Business API + tenant isolation tests (B-02, B-03, B-04).

Covers:
- Owner can read and update their own business
- Non-owner roles can read but not update
- User of Business B gets 404 on Business A (TenantScopedViewSet isolation)
- IsSameBusiness object-level check
- Unauthenticated access is rejected
- Logo upload (B-04)
"""

from io import BytesIO

import pytest
from PIL import Image
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

    def test_customer_uses_portal_not_business_api(self, customer_a, biz_a):
        """Customers get their mess's name from /auth/me/; the staff API is closed to them."""
        resp = auth_client(customer_a).get("/api/v1/business/")
        assert resp.status_code == 403

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
        assert resp.status_code == 403  # customers can't reach the business API at all

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


# ── Logo upload (B-04) ───────────────────────────────────────────────────


def _make_image():
    """Create a small in-memory PNG for upload tests."""
    buf = BytesIO()
    Image.new("RGB", (100, 100), color="red").save(buf, format="PNG")
    buf.seek(0)
    buf.name = "logo.png"
    return buf


@pytest.mark.django_db
class TestLogoUpload:
    def test_owner_can_upload_logo(self, owner_a, biz_a):
        client = auth_client(owner_a)
        resp = client.patch(
            f"/api/v1/business/{biz_a.id}/",
            {"logo": _make_image()},
            format="multipart",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["logo"].startswith("data:image/png;base64,")
        # The full profile comes back (the app keeps it as its business).
        assert body["id"] == str(biz_a.id) and body["status"] == biz_a.status
        biz_a.refresh_from_db()
        assert bytes(biz_a.logo_data).startswith(b"\x89PNG")
        # And it is served on every read — no /media/ URL needed.
        assert auth_client(owner_a).get(f"/api/v1/business/{biz_a.id}/").json()["logo"] == body["logo"]

    def test_jpeg_detected_from_bytes(self, owner_a, biz_a):
        buf = BytesIO()
        Image.new("RGB", (20, 20), color="blue").save(buf, format="JPEG")
        buf.seek(0)
        buf.name = "logo.png"  # wrong extension — the bytes decide
        resp = auth_client(owner_a).patch(f"/api/v1/business/{biz_a.id}/", {"logo": buf}, format="multipart")
        assert resp.status_code == 200
        assert resp.json()["logo"].startswith("data:image/jpeg;base64,")

    def test_non_image_rejected(self, owner_a, biz_a):
        fake = BytesIO(b"<html><script>alert(1)</script></html>")
        fake.name = "logo.png"
        resp = auth_client(owner_a).patch(f"/api/v1/business/{biz_a.id}/", {"logo": fake}, format="multipart")
        assert resp.status_code == 400
        biz_a.refresh_from_db()
        assert biz_a.logo_data is None

    def test_too_large_rejected(self, owner_a, biz_a):
        big = BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * (1024 * 1024))
        big.name = "logo.png"
        resp = auth_client(owner_a).patch(f"/api/v1/business/{biz_a.id}/", {"logo": big}, format="multipart")
        assert resp.status_code == 400

    def test_remove_logo(self, owner_a, biz_a):
        client = auth_client(owner_a)
        client.patch(f"/api/v1/business/{biz_a.id}/", {"logo": _make_image()}, format="multipart")
        resp = client.patch(f"/api/v1/business/{biz_a.id}/", {"logo": ""}, format="multipart")
        assert resp.status_code == 200
        assert resp.json()["logo"] is None

    def test_remove_logo_with_json_null(self, owner_a, biz_a):
        client = auth_client(owner_a)
        client.patch(f"/api/v1/business/{biz_a.id}/", {"logo": _make_image()}, format="multipart")
        resp = client.patch(f"/api/v1/business/{biz_a.id}/", {"logo": None}, format="json")
        assert resp.status_code == 200
        assert resp.json()["logo"] is None

    def test_text_update_keeps_logo_and_returns_full_profile(self, owner_a, biz_a):
        client = auth_client(owner_a)
        client.patch(f"/api/v1/business/{biz_a.id}/", {"logo": _make_image()}, format="multipart")
        resp = client.patch(f"/api/v1/business/{biz_a.id}/", {"phone": "9999999999"}, format="json")
        assert resp.status_code == 200
        assert resp.json()["phone"] == "9999999999"
        assert resp.json()["id"] == str(biz_a.id)
        assert resp.json()["logo"].startswith("data:image/png")

    def test_logo_field_nullable(self, owner_a, biz_a):
        """Business without a logo returns null."""
        resp = auth_client(owner_a).get(f"/api/v1/business/{biz_a.id}/")
        assert resp.json()["logo"] is None

    def test_non_owner_cannot_upload_logo(self, manager_a, biz_a):
        resp = auth_client(manager_a).patch(
            f"/api/v1/business/{biz_a.id}/",
            {"logo": _make_image()},
            format="multipart",
        )
        assert resp.status_code == 403
