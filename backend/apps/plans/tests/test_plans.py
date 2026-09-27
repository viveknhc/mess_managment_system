"""Plan CRUD, validation, isolation tests (P-02, P-03)."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.meals.models import Meal
from apps.plans.models import Plan
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
def owner_b(biz_b):
    return User.objects.create_user(username="owner_b", password="pass", role=Role.OWNER, business=biz_b)


@pytest.fixture()
def lunch_a(biz_a):
    return Meal.objects.create(business=biz_a, name="Lunch", price="50.00")


@pytest.fixture()
def dinner_a(biz_a):
    return Meal.objects.create(business=biz_a, name="Dinner", price="60.00")


@pytest.fixture()
def meal_b(biz_b):
    return Meal.objects.create(business=biz_b, name="Lunch B")


@pytest.fixture()
def plan_a(biz_a, lunch_a):
    return Plan.objects.create(
        business=biz_a,
        name="Monthly Lunch",
        meal=lunch_a,
        duration_days=30,
        total_meals=30,
        price=Decimal("2500.00"),
    )


@pytest.fixture()
def plan_b(biz_b, meal_b):
    return Plan.objects.create(
        business=biz_b,
        name="Weekly Lunch",
        meal=meal_b,
        duration_days=7,
        total_meals=7,
        price=Decimal("500.00"),
    )


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


URL = "/api/v1/plans/"


def detail_url(pk):
    return f"{URL}{pk}/"


# ── List ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPlanList:
    def test_owner_lists(self, owner_a, plan_a):
        resp = auth_client(owner_a).get(URL)
        assert resp.status_code == 200
        assert resp.json()["count"] == 1
        assert resp.json()["results"][0]["meal_name"] == "Lunch"

    def test_delivery_can_list(self, delivery_a, plan_a):
        resp = auth_client(delivery_a).get(URL)
        assert resp.status_code == 200

    def test_filter_active(self, owner_a, plan_a):
        plan_a.is_active = False
        plan_a.save()
        resp = auth_client(owner_a).get(URL, {"is_active": "true"})
        assert resp.json()["count"] == 0

    def test_filter_by_meal(self, owner_a, plan_a, dinner_a, biz_a):
        Plan.objects.create(
            business=biz_a,
            name="Dinner Plan",
            meal=dinner_a,
            duration_days=30,
            total_meals=30,
            price=Decimal("3000.00"),
        )
        resp = auth_client(owner_a).get(URL, {"meal": str(dinner_a.id)})
        assert resp.json()["count"] == 1
        assert resp.json()["results"][0]["name"] == "Dinner Plan"


# ── Create ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPlanCreate:
    def test_owner_creates(self, owner_a, lunch_a, biz_a):
        resp = auth_client(owner_a).post(
            URL,
            {
                "name": "Weekly Lunch",
                "meal": str(lunch_a.id),
                "duration_days": 7,
                "total_meals": 7,
                "price": "500.00",
            },
            format="json",
        )
        assert resp.status_code == 201
        plan = Plan.objects.get(name="Weekly Lunch")
        assert plan.business_id == biz_a.id
        assert plan.price == Decimal("500.00")

    def test_manager_creates(self, manager_a, lunch_a):
        resp = auth_client(manager_a).post(
            URL,
            {
                "name": "Manager Plan",
                "meal": str(lunch_a.id),
                "duration_days": 15,
                "total_meals": 15,
                "price": "1200.00",
            },
            format="json",
        )
        assert resp.status_code == 201

    def test_delivery_cannot_create(self, delivery_a, lunch_a):
        resp = auth_client(delivery_a).post(
            URL,
            {
                "name": "Hack",
                "meal": str(lunch_a.id),
                "duration_days": 7,
                "total_meals": 7,
                "price": "500.00",
            },
            format="json",
        )
        assert resp.status_code == 403

    def test_duplicate_name_rejected(self, owner_a, plan_a, lunch_a):
        resp = auth_client(owner_a).post(
            URL,
            {
                "name": "Monthly Lunch",
                "meal": str(lunch_a.id),
                "duration_days": 30,
                "total_meals": 30,
                "price": "2500.00",
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_skip_pause_flags(self, owner_a, lunch_a):
        resp = auth_client(owner_a).post(
            URL,
            {
                "name": "Flex Plan",
                "meal": str(lunch_a.id),
                "duration_days": 30,
                "total_meals": 25,
                "price": "2000.00",
                "skip_allowed": True,
                "pause_allowed": True,
            },
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["skip_allowed"] is True
        assert data["pause_allowed"] is True


# ── Validation (P-02) ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPlanValidation:
    def test_total_meals_exceeds_duration(self, owner_a, lunch_a):
        resp = auth_client(owner_a).post(
            URL,
            {
                "name": "Bad Plan",
                "meal": str(lunch_a.id),
                "duration_days": 7,
                "total_meals": 10,
                "price": "500.00",
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_price_zero_allowed(self, owner_a, lunch_a):
        resp = auth_client(owner_a).post(
            URL,
            {
                "name": "Free Plan",
                "meal": str(lunch_a.id),
                "duration_days": 7,
                "total_meals": 7,
                "price": "0.00",
            },
            format="json",
        )
        assert resp.status_code == 201

    def test_cross_business_meal_rejected(self, owner_a, meal_b):
        """Cannot create plan with a meal from another business."""
        resp = auth_client(owner_a).post(
            URL,
            {
                "name": "Cross Biz",
                "meal": str(meal_b.id),
                "duration_days": 7,
                "total_meals": 7,
                "price": "500.00",
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_inactive_meal_rejected(self, owner_a, lunch_a):
        lunch_a.is_active = False
        lunch_a.save()
        resp = auth_client(owner_a).post(
            URL,
            {
                "name": "Dead Meal Plan",
                "meal": str(lunch_a.id),
                "duration_days": 7,
                "total_meals": 7,
                "price": "500.00",
            },
            format="json",
        )
        assert resp.status_code == 400


# ── Update ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPlanUpdate:
    def test_owner_updates(self, owner_a, plan_a):
        resp = auth_client(owner_a).patch(detail_url(plan_a.id), {"price": "2800.00"}, format="json")
        assert resp.status_code == 200
        plan_a.refresh_from_db()
        assert plan_a.price == Decimal("2800.00")

    def test_toggle_active(self, owner_a, plan_a):
        resp = auth_client(owner_a).patch(detail_url(plan_a.id), {"is_active": False}, format="json")
        assert resp.status_code == 200
        plan_a.refresh_from_db()
        assert plan_a.is_active is False

    def test_delivery_cannot_update(self, delivery_a, plan_a):
        resp = auth_client(delivery_a).patch(detail_url(plan_a.id), {"price": "1.00"}, format="json")
        assert resp.status_code == 403


# ── Soft-delete ───────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPlanSoftDelete:
    def test_delete_deactivates(self, owner_a, plan_a):
        resp = auth_client(owner_a).delete(detail_url(plan_a.id))
        assert resp.status_code == 204
        plan_a.refresh_from_db()
        assert plan_a.is_active is False

    def test_manager_cannot_delete(self, manager_a, plan_a):
        resp = auth_client(manager_a).delete(detail_url(plan_a.id))
        assert resp.status_code == 403


# ── Tenant isolation ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPlanIsolation:
    def test_owner_b_cannot_see_biz_a_plans(self, owner_b, plan_a):
        resp = auth_client(owner_b).get(URL)
        assert resp.json()["count"] == 0

    def test_owner_b_gets_404_on_biz_a_plan(self, owner_b, plan_a):
        resp = auth_client(owner_b).get(detail_url(plan_a.id))
        assert resp.status_code == 404

    def test_owner_b_cannot_update_biz_a_plan(self, owner_b, plan_a):
        resp = auth_client(owner_b).patch(detail_url(plan_a.id), {"price": "1.00"}, format="json")
        assert resp.status_code == 404

    def test_both_see_only_own(self, owner_a, owner_b, plan_a, plan_b):
        resp_a = auth_client(owner_a).get(URL)
        resp_b = auth_client(owner_b).get(URL)
        ids_a = {r["id"] for r in resp_a.json()["results"]}
        ids_b = {r["id"] for r in resp_b.json()["results"]}
        assert ids_a.isdisjoint(ids_b)
