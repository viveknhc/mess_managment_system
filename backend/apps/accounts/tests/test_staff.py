"""Staff management tests (U-02, U-03).

Covers:
- CRUD operations (owner can create/read/update/deactivate staff)
- Role permission matrix (manager read-only, staff/customer blocked)
- Tenant isolation (business B gets 404 on business A staff)
- Activate/deactivate actions
- Last-owner protection
- Invite flow placeholder (U-04: create with temp password)
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
    return User.objects.create_user(
        username="owner_a", password="pass", name="Owner A", role=Role.OWNER, business=biz_a
    )


@pytest.fixture()
def owner_b(biz_b):
    return User.objects.create_user(
        username="owner_b", password="pass", name="Owner B", role=Role.OWNER, business=biz_b
    )


@pytest.fixture()
def manager_a(biz_a):
    return User.objects.create_user(
        username="manager_a", password="pass", name="Manager A", role=Role.MANAGER, business=biz_a
    )


@pytest.fixture()
def delivery_a(biz_a):
    return User.objects.create_user(
        username="delivery_a",
        password="pass",
        name="Delivery A",
        role=Role.DELIVERY_STAFF,
        business=biz_a,
    )


@pytest.fixture()
def customer_a(biz_a):
    return User.objects.create_user(
        username="customer_a", password="pass", name="Customer A", role=Role.CUSTOMER, business=biz_a
    )


@pytest.fixture()
def staff_b(biz_b):
    """A delivery staff in business B — for isolation tests."""
    return User.objects.create_user(
        username="delivery_b",
        password="pass",
        name="Delivery B",
        role=Role.DELIVERY_STAFF,
        business=biz_b,
    )


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


STAFF_URL = "/api/v1/staff/"


def detail_url(pk):
    return f"{STAFF_URL}{pk}/"


# ── List ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestStaffList:
    def test_owner_lists_staff(self, owner_a, manager_a, delivery_a):
        resp = auth_client(owner_a).get(STAFF_URL)
        assert resp.status_code == 200
        names = [r["name"] for r in resp.json()["results"]]
        # Owner sees other staff but NOT themselves
        assert "Manager A" in names
        assert "Delivery A" in names
        assert "Owner A" not in names

    def test_manager_can_list(self, manager_a, delivery_a):
        resp = auth_client(manager_a).get(STAFF_URL)
        assert resp.status_code == 200

    def test_delivery_staff_cannot_list(self, delivery_a):
        resp = auth_client(delivery_a).get(STAFF_URL)
        assert resp.status_code == 403

    def test_customer_cannot_list(self, customer_a):
        resp = auth_client(customer_a).get(STAFF_URL)
        assert resp.status_code == 403

    def test_unauthenticated_rejected(self, db):
        resp = APIClient().get(STAFF_URL)
        assert resp.status_code == 401

    def test_customers_excluded_from_list(self, owner_a, customer_a):
        """Customer users don't appear in the staff list."""
        resp = auth_client(owner_a).get(STAFF_URL)
        names = [r["name"] for r in resp.json()["results"]]
        assert "Customer A" not in names


# ── Retrieve ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestStaffRetrieve:
    def test_owner_retrieves_staff(self, owner_a, delivery_a):
        resp = auth_client(owner_a).get(detail_url(delivery_a.id))
        assert resp.status_code == 200
        assert resp.json()["name"] == "Delivery A"

    def test_manager_retrieves_staff(self, manager_a, delivery_a):
        resp = auth_client(manager_a).get(detail_url(delivery_a.id))
        assert resp.status_code == 200


# ── Create ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestStaffCreate:
    def test_owner_creates_staff(self, owner_a, biz_a):
        resp = auth_client(owner_a).post(
            STAFF_URL,
            {
                "username": "new_staff",
                "password": "securepass123",
                "name": "New Staff",
                "role": Role.DELIVERY_STAFF,
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["username"] == "new_staff"
        assert resp.json()["role"] == Role.DELIVERY_STAFF
        # Verify business was set server-side
        user = User.objects.get(username="new_staff")
        assert user.business_id == biz_a.id

    def test_created_staff_can_login(self, owner_a):
        """U-04: Invite flow — created user can log in with the given password."""
        auth_client(owner_a).post(
            STAFF_URL,
            {
                "username": "invite_user",
                "password": "temppass123",
                "name": "Invited",
                "role": Role.MANAGER,
            },
            format="json",
        )
        # Login as the new user
        client = APIClient()
        resp = client.post(
            "/api/v1/auth/login/",
            {"username": "invite_user", "password": "temppass123"},
        )
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == Role.MANAGER

    def test_manager_cannot_create(self, manager_a):
        resp = auth_client(manager_a).post(
            STAFF_URL,
            {
                "username": "hack",
                "password": "securepass123",
                "name": "Hack",
                "role": Role.DELIVERY_STAFF,
            },
            format="json",
        )
        assert resp.status_code == 403

    def test_cannot_create_customer_role(self, owner_a):
        resp = auth_client(owner_a).post(
            STAFF_URL,
            {
                "username": "cust",
                "password": "securepass123",
                "name": "Cust",
                "role": Role.CUSTOMER,
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_cannot_create_super_admin_role(self, owner_a):
        resp = auth_client(owner_a).post(
            STAFF_URL,
            {
                "username": "sa",
                "password": "securepass123",
                "name": "SA",
                "role": Role.SUPER_ADMIN,
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_duplicate_username_rejected(self, owner_a, delivery_a):
        resp = auth_client(owner_a).post(
            STAFF_URL,
            {
                "username": "delivery_a",
                "password": "securepass123",
                "name": "Dup",
                "role": Role.DELIVERY_STAFF,
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_short_password_rejected(self, owner_a):
        resp = auth_client(owner_a).post(
            STAFF_URL,
            {
                "username": "shortpw",
                "password": "abc",
                "name": "Short",
                "role": Role.DELIVERY_STAFF,
            },
            format="json",
        )
        assert resp.status_code == 400


# ── Update ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestStaffUpdate:
    def test_owner_updates_staff(self, owner_a, delivery_a):
        resp = auth_client(owner_a).patch(
            detail_url(delivery_a.id),
            {"name": "Updated Name", "role": Role.KITCHEN_STAFF},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"
        assert resp.json()["role"] == Role.KITCHEN_STAFF

    def test_manager_cannot_update(self, manager_a, delivery_a):
        resp = auth_client(manager_a).patch(
            detail_url(delivery_a.id),
            {"name": "Hacked"},
            format="json",
        )
        assert resp.status_code == 403

    def test_last_owner_cannot_be_demoted(self, owner_a, delivery_a):
        """Protect last active owner from role change."""
        resp = auth_client(owner_a).patch(
            detail_url(owner_a.id),
            {"role": Role.MANAGER},
            format="json",
        )
        # Owner excludes self from queryset, so this is 404
        assert resp.status_code == 404


# ── Activate / Deactivate ────────────────────────────────────────────────


@pytest.mark.django_db
class TestStaffActivation:
    def test_owner_deactivates_staff(self, owner_a, delivery_a):
        resp = auth_client(owner_a).post(f"{detail_url(delivery_a.id)}deactivate/")
        assert resp.status_code == 200
        delivery_a.refresh_from_db()
        assert delivery_a.is_active is False

    def test_owner_activates_staff(self, owner_a, delivery_a):
        delivery_a.is_active = False
        delivery_a.save()
        resp = auth_client(owner_a).post(f"{detail_url(delivery_a.id)}activate/")
        assert resp.status_code == 200
        delivery_a.refresh_from_db()
        assert delivery_a.is_active is True

    def test_deactivated_staff_cannot_login(self, owner_a, delivery_a):
        auth_client(owner_a).post(f"{detail_url(delivery_a.id)}deactivate/")
        client = APIClient()
        resp = client.post(
            "/api/v1/auth/login/",
            {"username": "delivery_a", "password": "pass"},
        )
        assert resp.status_code == 401

    def test_delete_soft_deactivates(self, owner_a, delivery_a):
        resp = auth_client(owner_a).delete(detail_url(delivery_a.id))
        assert resp.status_code == 204
        delivery_a.refresh_from_db()
        assert delivery_a.is_active is False

    def test_manager_cannot_deactivate(self, manager_a, delivery_a):
        resp = auth_client(manager_a).post(f"{detail_url(delivery_a.id)}deactivate/")
        assert resp.status_code == 403


# ── Tenant isolation (U-03) ──────────────────────────────────────────────


@pytest.mark.django_db
class TestStaffTenantIsolation:
    """Business B users get 404 on Business A staff."""

    def test_owner_b_cannot_list_biz_a_staff(self, owner_b, delivery_a):
        resp = auth_client(owner_b).get(STAFF_URL)
        ids = [r["id"] for r in resp.json()["results"]]
        assert str(delivery_a.id) not in ids

    def test_owner_b_gets_404_on_biz_a_staff(self, owner_b, delivery_a):
        resp = auth_client(owner_b).get(detail_url(delivery_a.id))
        assert resp.status_code == 404

    def test_owner_b_cannot_update_biz_a_staff(self, owner_b, delivery_a):
        resp = auth_client(owner_b).patch(detail_url(delivery_a.id), {"name": "Stolen"}, format="json")
        assert resp.status_code == 404
        delivery_a.refresh_from_db()
        assert delivery_a.name == "Delivery A"

    def test_owner_b_cannot_deactivate_biz_a_staff(self, owner_b, delivery_a):
        resp = auth_client(owner_b).post(f"{detail_url(delivery_a.id)}deactivate/")
        assert resp.status_code == 404

    def test_both_businesses_see_only_own_staff(self, owner_a, owner_b, delivery_a, staff_b):
        resp_a = auth_client(owner_a).get(STAFF_URL)
        resp_b = auth_client(owner_b).get(STAFF_URL)

        ids_a = {r["id"] for r in resp_a.json()["results"]}
        ids_b = {r["id"] for r in resp_b.json()["results"]}

        assert str(delivery_a.id) in ids_a
        assert str(staff_b.id) in ids_b
        assert ids_a.isdisjoint(ids_b)


# ── Login-as-staff smoke check (U-06) ────────────────────────────────────


@pytest.mark.django_db
class TestLoginAsStaff:
    """Each role can log in and gets correct user data."""

    @pytest.mark.parametrize(
        "role",
        [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF, Role.CUSTOMER],
    )
    def test_role_can_login(self, biz_a, role):
        User.objects.create_user(
            username=f"test_{role.lower()}",
            password="testpass123",
            role=role,
            business=biz_a,
        )
        client = APIClient()
        resp = client.post(
            "/api/v1/auth/login/",
            {"username": f"test_{role.lower()}", "password": "testpass123"},
        )
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == role
