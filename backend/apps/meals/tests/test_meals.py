"""Meal CRUD + isolation tests (M-02)."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.meals.models import Meal
from common.constants import Role


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
def customer_a(biz_a):
    return User.objects.create_user(
        username="customer_a", password="pass", role=Role.CUSTOMER, business=biz_a
    )


@pytest.fixture()
def owner_b(biz_b):
    return User.objects.create_user(username="owner_b", password="pass", role=Role.OWNER, business=biz_b)


@pytest.fixture()
def breakfast(biz_a):
    return Meal.objects.create(business=biz_a, name="Breakfast")


@pytest.fixture()
def lunch(biz_a):
    return Meal.objects.create(business=biz_a, name="Lunch", price="50.00")


@pytest.fixture()
def meal_b(biz_b):
    return Meal.objects.create(business=biz_b, name="Dinner")


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


URL = "/api/v1/meals/"


def detail_url(pk):
    return f"{URL}{pk}/"


@pytest.mark.django_db
class TestMealList:
    def test_owner_lists(self, owner_a, breakfast, lunch):
        resp = auth_client(owner_a).get(URL)
        assert resp.status_code == 200
        assert resp.json()["count"] == 2

    def test_delivery_can_list(self, delivery_a, breakfast):
        resp = auth_client(delivery_a).get(URL)
        assert resp.status_code == 200

    def test_customer_cannot_list(self, customer_a, breakfast):
        resp = auth_client(customer_a).get(URL)
        assert resp.status_code == 403

    def test_filter_active(self, owner_a, breakfast, lunch):
        lunch.is_active = False
        lunch.save()
        resp = auth_client(owner_a).get(URL, {"is_active": "true"})
        assert resp.json()["count"] == 1
        assert resp.json()["results"][0]["name"] == "Breakfast"

    def test_filter_inactive(self, owner_a, breakfast, lunch):
        lunch.is_active = False
        lunch.save()
        resp = auth_client(owner_a).get(URL, {"is_active": "false"})
        assert resp.json()["count"] == 1
        assert resp.json()["results"][0]["name"] == "Lunch"


@pytest.mark.django_db
class TestMealCreate:
    def test_owner_creates(self, owner_a, biz_a):
        resp = auth_client(owner_a).post(URL, {"name": "Dinner", "price": "75.00"}, format="json")
        assert resp.status_code == 201
        meal = Meal.objects.get(name="Dinner")
        assert meal.business_id == biz_a.id
        assert str(meal.price) == "75.00"

    def test_manager_creates(self, manager_a):
        resp = auth_client(manager_a).post(URL, {"name": "Snacks"}, format="json")
        assert resp.status_code == 201

    def test_delivery_cannot_create(self, delivery_a):
        resp = auth_client(delivery_a).post(URL, {"name": "Hack"}, format="json")
        assert resp.status_code == 403

    def test_duplicate_name_rejected(self, owner_a, breakfast):
        resp = auth_client(owner_a).post(URL, {"name": "Breakfast"}, format="json")
        assert resp.status_code == 400

    def test_duplicate_name_case_insensitive(self, owner_a, breakfast):
        resp = auth_client(owner_a).post(URL, {"name": "breakfast"}, format="json")
        assert resp.status_code == 400

    def test_price_nullable(self, owner_a):
        resp = auth_client(owner_a).post(URL, {"name": "Free Meal"}, format="json")
        assert resp.status_code == 201
        assert resp.json()["price"] is None


@pytest.mark.django_db
class TestMealUpdate:
    def test_owner_updates(self, owner_a, breakfast):
        resp = auth_client(owner_a).patch(detail_url(breakfast.id), {"name": "Morning Meal"}, format="json")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Morning Meal"

    def test_toggle_active(self, owner_a, breakfast):
        resp = auth_client(owner_a).patch(detail_url(breakfast.id), {"is_active": False}, format="json")
        assert resp.status_code == 200
        breakfast.refresh_from_db()
        assert breakfast.is_active is False

    def test_delivery_cannot_update(self, delivery_a, breakfast):
        resp = auth_client(delivery_a).patch(detail_url(breakfast.id), {"name": "Hack"}, format="json")
        assert resp.status_code == 403


@pytest.mark.django_db
class TestMealSoftDelete:
    def test_delete_deactivates(self, owner_a, breakfast):
        resp = auth_client(owner_a).delete(detail_url(breakfast.id))
        assert resp.status_code == 204
        breakfast.refresh_from_db()
        assert breakfast.is_active is False

    def test_manager_cannot_delete(self, manager_a, breakfast):
        resp = auth_client(manager_a).delete(detail_url(breakfast.id))
        assert resp.status_code == 403


@pytest.mark.django_db
class TestMealIsolation:
    def test_owner_b_cannot_see_biz_a_meals(self, owner_b, breakfast):
        resp = auth_client(owner_b).get(URL)
        assert resp.json()["count"] == 0

    def test_owner_b_gets_404_on_biz_a_meal(self, owner_b, breakfast):
        resp = auth_client(owner_b).get(detail_url(breakfast.id))
        assert resp.status_code == 404

    def test_owner_b_cannot_update_biz_a_meal(self, owner_b, breakfast):
        resp = auth_client(owner_b).patch(detail_url(breakfast.id), {"name": "Stolen"}, format="json")
        assert resp.status_code == 404

    def test_both_see_only_own(self, owner_a, owner_b, breakfast, meal_b):
        resp_a = auth_client(owner_a).get(URL)
        resp_b = auth_client(owner_b).get(URL)
        ids_a = {r["id"] for r in resp_a.json()["results"]}
        ids_b = {r["id"] for r in resp_b.json()["results"]}
        assert ids_a.isdisjoint(ids_b)


@pytest.mark.django_db
class TestBootstrapSeeds:
    def test_bootstrap_creates_default_meals(self, db):
        from io import StringIO

        from django.core.management import call_command

        call_command(
            "bootstrap_business",
            business_name="Test Mess",
            owner_username="test_owner",
            owner_password="testpass123",
            stdout=StringIO(),
        )
        biz = Business.objects.get(name="Test Mess")
        meals = list(Meal.objects.filter(business=biz).values_list("name", flat=True))
        assert sorted(meals) == ["Breakfast", "Dinner", "Lunch", "Snacks"]
