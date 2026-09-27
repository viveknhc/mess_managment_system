"""Customer CRUD, search, filters, isolation tests (C-06)."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from common.constants import Role

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture()
def biz_a(db):
    return Business.objects.create(name="Mess A")


@pytest.fixture()
def biz_b(db):
    return Business.objects.create(name="Mess B")


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


@pytest.fixture()
def customer_user_a(biz_a):
    return User.objects.create_user(
        username="customer_a", password="pass", role=Role.CUSTOMER, business=biz_a
    )


@pytest.fixture()
def owner_b(biz_b):
    return User.objects.create_user(username="owner_b", password="pass", role=Role.OWNER, business=biz_b)


@pytest.fixture()
def cust_a(biz_a):
    return Customer.objects.create(business=biz_a, name="Alice", phone="1111111111")


@pytest.fixture()
def cust_a2(biz_a):
    return Customer.objects.create(business=biz_a, name="Bob", phone="2222222222", address="123 Main St")


@pytest.fixture()
def cust_b(biz_b):
    return Customer.objects.create(business=biz_b, name="Charlie", phone="3333333333")


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


URL = "/api/v1/customers/"


def detail_url(pk):
    return f"{URL}{pk}/"


# ── Customer code auto-generation ─────────────────────────────────────────


@pytest.mark.django_db
class TestCustomerCode:
    def test_auto_generated_on_create(self, cust_a):
        assert cust_a.customer_code == "CUST-0001"

    def test_sequential_per_business(self, cust_a, cust_a2):
        assert cust_a.customer_code == "CUST-0001"
        assert cust_a2.customer_code == "CUST-0002"

    def test_independent_per_business(self, cust_a, cust_b):
        """Each business starts its own sequence."""
        assert cust_a.customer_code == "CUST-0001"
        assert cust_b.customer_code == "CUST-0001"

    def test_unique_constraint(self, biz_a, cust_a):
        """Cannot create duplicate code within same business."""
        from django.db import IntegrityError

        dup = Customer(business=biz_a, name="Dup", customer_code="CUST-0001")
        with pytest.raises(IntegrityError):
            dup.save()


# ── List ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCustomerList:
    def test_owner_lists_customers(self, owner_a, cust_a, cust_a2):
        resp = auth_client(owner_a).get(URL)
        assert resp.status_code == 200
        assert resp.json()["count"] == 2

    def test_manager_can_list(self, manager_a, cust_a):
        resp = auth_client(manager_a).get(URL)
        assert resp.status_code == 200

    def test_delivery_can_list(self, delivery_a, cust_a):
        resp = auth_client(delivery_a).get(URL)
        assert resp.status_code == 200

    def test_customer_role_cannot_list(self, customer_user_a, cust_a):
        resp = auth_client(customer_user_a).get(URL)
        assert resp.status_code == 403

    def test_unauthenticated_rejected(self, cust_a):
        resp = APIClient().get(URL)
        assert resp.status_code == 401


# ── Create ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCustomerCreate:
    def test_owner_creates_customer(self, owner_a, biz_a):
        resp = auth_client(owner_a).post(URL, {"name": "New Customer", "phone": "9999999999"}, format="json")
        assert resp.status_code == 201
        assert resp.json()["name"] == "New Customer"
        # Verify business and code set server-side
        cust = Customer.objects.get(name="New Customer")
        assert cust.business_id == biz_a.id
        assert cust.customer_code == "CUST-0001"

    def test_manager_creates_customer(self, manager_a):
        resp = auth_client(manager_a).post(URL, {"name": "Mgr Customer"}, format="json")
        assert resp.status_code == 201

    def test_delivery_cannot_create(self, delivery_a):
        resp = auth_client(delivery_a).post(URL, {"name": "Hack"}, format="json")
        assert resp.status_code == 403

    def test_duplicate_phone_rejected(self, owner_a, cust_a):
        resp = auth_client(owner_a).post(URL, {"name": "Dup", "phone": "1111111111"}, format="json")
        assert resp.status_code == 400

    def test_empty_phone_allowed(self, owner_a):
        """Multiple customers without phone should be fine."""
        auth_client(owner_a).post(URL, {"name": "No Phone 1"}, format="json")
        resp = auth_client(owner_a).post(URL, {"name": "No Phone 2"}, format="json")
        assert resp.status_code == 201


# ── Retrieve ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCustomerRetrieve:
    def test_owner_retrieves(self, owner_a, cust_a):
        resp = auth_client(owner_a).get(detail_url(cust_a.id))
        assert resp.status_code == 200
        data = resp.json()
        assert data["customer_code"] == "CUST-0001"
        assert "notes" in data  # detail serializer has notes
        assert "address" in data

    def test_delivery_retrieves(self, delivery_a, cust_a):
        resp = auth_client(delivery_a).get(detail_url(cust_a.id))
        assert resp.status_code == 200


# ── Update ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCustomerUpdate:
    def test_owner_updates(self, owner_a, cust_a):
        resp = auth_client(owner_a).patch(
            detail_url(cust_a.id), {"name": "Alice Updated", "status": "BLOCKED"}, format="json"
        )
        assert resp.status_code == 200
        cust_a.refresh_from_db()
        assert cust_a.name == "Alice Updated"
        assert cust_a.status == "BLOCKED"

    def test_manager_updates(self, manager_a, cust_a):
        resp = auth_client(manager_a).patch(detail_url(cust_a.id), {"name": "Mgr Edit"}, format="json")
        assert resp.status_code == 200

    def test_delivery_cannot_update(self, delivery_a, cust_a):
        resp = auth_client(delivery_a).patch(detail_url(cust_a.id), {"name": "Hack"}, format="json")
        assert resp.status_code == 403

    def test_duplicate_phone_on_update_rejected(self, owner_a, cust_a, cust_a2):
        resp = auth_client(owner_a).patch(detail_url(cust_a.id), {"phone": "2222222222"}, format="json")
        assert resp.status_code == 400

    def test_same_phone_on_self_allowed(self, owner_a, cust_a):
        """Updating other fields shouldn't fail phone uniqueness for own phone."""
        resp = auth_client(owner_a).patch(
            detail_url(cust_a.id), {"phone": "1111111111", "name": "Same Phone"}, format="json"
        )
        assert resp.status_code == 200


# ── Soft-delete (C-08) ───────────────────────────────────────────────────


@pytest.mark.django_db
class TestCustomerSoftDelete:
    def test_delete_sets_inactive(self, owner_a, cust_a):
        resp = auth_client(owner_a).delete(detail_url(cust_a.id))
        assert resp.status_code == 204
        cust_a.refresh_from_db()
        assert cust_a.status == "INACTIVE"

    def test_manager_cannot_delete(self, manager_a, cust_a):
        resp = auth_client(manager_a).delete(detail_url(cust_a.id))
        assert resp.status_code == 403


# ── Search + Filters (C-05) ──────────────────────────────────────────────


@pytest.mark.django_db
class TestCustomerSearch:
    def test_search_by_name(self, owner_a, cust_a, cust_a2):
        resp = auth_client(owner_a).get(URL, {"search": "alice"})
        assert resp.json()["count"] == 1
        assert resp.json()["results"][0]["name"] == "Alice"

    def test_search_by_phone(self, owner_a, cust_a, cust_a2):
        resp = auth_client(owner_a).get(URL, {"search": "2222"})
        assert resp.json()["count"] == 1
        assert resp.json()["results"][0]["name"] == "Bob"

    def test_search_by_code(self, owner_a, cust_a, cust_a2):
        resp = auth_client(owner_a).get(URL, {"search": "CUST-0001"})
        assert resp.json()["count"] == 1

    def test_search_by_address(self, owner_a, cust_a, cust_a2):
        resp = auth_client(owner_a).get(URL, {"search": "Main St"})
        assert resp.json()["count"] == 1
        assert resp.json()["results"][0]["name"] == "Bob"

    def test_search_no_match(self, owner_a, cust_a):
        resp = auth_client(owner_a).get(URL, {"search": "zzzzz"})
        assert resp.json()["count"] == 0

    def test_filter_by_status(self, owner_a, cust_a, cust_a2):
        cust_a2.status = "BLOCKED"
        cust_a2.save()
        resp = auth_client(owner_a).get(URL, {"status": "BLOCKED"})
        assert resp.json()["count"] == 1
        assert resp.json()["results"][0]["name"] == "Bob"

    def test_pagination(self, owner_a, biz_a):
        for i in range(25):
            Customer.objects.create(business=biz_a, name=f"Cust {i:02d}")
        resp = auth_client(owner_a).get(URL)
        data = resp.json()
        assert data["count"] == 25
        assert len(data["results"]) == 20  # PAGE_SIZE=20
        assert data["next"] is not None


# ── Tenant isolation ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCustomerIsolation:
    def test_owner_b_cannot_see_biz_a_customers(self, owner_b, cust_a):
        resp = auth_client(owner_b).get(URL)
        assert resp.json()["count"] == 0

    def test_owner_b_gets_404_on_biz_a_customer(self, owner_b, cust_a):
        resp = auth_client(owner_b).get(detail_url(cust_a.id))
        assert resp.status_code == 404

    def test_owner_b_cannot_update_biz_a_customer(self, owner_b, cust_a):
        resp = auth_client(owner_b).patch(detail_url(cust_a.id), {"name": "Stolen"}, format="json")
        assert resp.status_code == 404
        cust_a.refresh_from_db()
        assert cust_a.name == "Alice"

    def test_owner_b_cannot_delete_biz_a_customer(self, owner_b, cust_a):
        resp = auth_client(owner_b).delete(detail_url(cust_a.id))
        assert resp.status_code == 404

    def test_both_see_only_own(self, owner_a, owner_b, cust_a, cust_b):
        resp_a = auth_client(owner_a).get(URL)
        resp_b = auth_client(owner_b).get(URL)
        ids_a = {r["id"] for r in resp_a.json()["results"]}
        ids_b = {r["id"] for r in resp_b.json()["results"]}
        assert str(cust_a.id) in ids_a
        assert str(cust_b.id) in ids_b
        assert ids_a.isdisjoint(ids_b)
