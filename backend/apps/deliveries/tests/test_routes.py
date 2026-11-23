"""Delivery routes (feature ``delivery_routes``): customers grouped under one delivery
staff member, whose deliveries are assigned to them — on generation and whenever the
route, its staff or its customers change. Plus feature gating and tenant isolation."""

import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.customization.registry import DELIVERY_ROUTES
from apps.customization.services import FeatureService
from apps.deliveries.models import Delivery, DeliveryRoute, DeliveryStatus
from apps.deliveries.services import RouteService
from apps.meals.models import Meal
from apps.plans.models import Plan
from apps.subscriptions.services import SubscriptionService
from common.constants import Role

TODAY = datetime.date.today()
ROUTES = "/api/v1/delivery-routes/"


def client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture()
def biz(db):
    b = Business.objects.create(name="Route Mess")
    FeatureService.set_overrides(b.id, {DELIVERY_ROUTES: True})
    return b


@pytest.fixture()
def other_biz(db):
    b = Business.objects.create(name="Other Mess")
    FeatureService.set_overrides(b.id, {DELIVERY_ROUTES: True})
    return b


@pytest.fixture()
def owner(biz):
    return User.objects.create_user(username="owner", password="pass", role=Role.OWNER, business=biz)


def rider(business, username):
    return User.objects.create_user(
        username=username, password="pass", role=Role.DELIVERY_STAFF, business=business, name=username.title()
    )


@pytest.fixture()
def suresh(biz):
    return rider(biz, "suresh")


@pytest.fixture()
def anil(biz):
    return rider(biz, "anil")


@pytest.fixture()
def plan(biz):
    meal = Meal.objects.create(business=biz, name="Lunch")
    return Plan.objects.create(
        business=biz, name="Monthly", meal=meal, duration_days=5, total_meals=5, price=Decimal("0.00")
    )


_phone = iter(range(9000000000, 9100000000))


def customer(business, name):
    return Customer.objects.create(business=business, name=name, phone=str(next(_phone)))


def subscribe(business, plan, cust):
    """A ₹0 plan activates at once, so deliveries exist from today."""
    return SubscriptionService.create_subscription(
        business_id=business.id, customer=cust, plan=plan, start_date=TODAY
    )


def staff_of(cust):
    return set(Delivery.objects.filter(customer=cust).values_list("assigned_staff_id", flat=True))


@pytest.mark.django_db
class TestAssignment:
    def test_new_deliveries_go_to_route_staff(self, biz, suresh, plan):
        route = RouteService.save_route(business_id=biz.id, name="Kakkanad", staff=suresh)
        cust = customer(biz, "Rahul")
        cust.route = route
        cust.save()
        subscribe(biz, plan, cust)
        assert staff_of(cust) == {suresh.id}

    def test_customer_without_route_stays_open(self, biz, plan):
        cust = customer(biz, "Rahul")
        subscribe(biz, plan, cust)
        assert staff_of(cust) == {None}

    def test_feature_off_assigns_nobody(self, biz, suresh, plan):
        route = RouteService.save_route(business_id=biz.id, name="Kakkanad", staff=suresh)
        FeatureService.set_overrides(biz.id, {DELIVERY_ROUTES: False})
        cust = customer(biz, "Rahul")
        cust.route = route
        cust.save()
        subscribe(biz, plan, cust)
        assert staff_of(cust) == {None}

    def test_adding_customers_reassigns_upcoming_deliveries(self, biz, suresh, plan):
        cust = customer(biz, "Rahul")
        subscribe(biz, plan, cust)
        RouteService.save_route(business_id=biz.id, name="Kakkanad", staff=suresh, customer_ids=[cust.id])
        assert staff_of(cust) == {suresh.id}

    def test_changing_route_staff_moves_deliveries(self, biz, suresh, anil, plan):
        cust = customer(biz, "Rahul")
        subscribe(biz, plan, cust)
        route = RouteService.save_route(
            business_id=biz.id, name="Kakkanad", staff=suresh, customer_ids=[cust.id]
        )
        RouteService.save_route(business_id=biz.id, route=route, name="Kakkanad", staff=anil)
        assert staff_of(cust) == {anil.id}

    def test_done_deliveries_keep_who_delivered(self, biz, suresh, anil, plan):
        cust = customer(biz, "Rahul")
        sub = subscribe(biz, plan, cust)
        route = RouteService.save_route(
            business_id=biz.id, name="Kakkanad", staff=suresh, customer_ids=[cust.id]
        )
        done = Delivery.objects.get(subscription=sub, delivery_date=TODAY)
        Delivery.objects.filter(pk=done.pk).update(status=DeliveryStatus.DELIVERED)
        RouteService.save_route(business_id=biz.id, route=route, name="Kakkanad", staff=anil)
        done.refresh_from_db()
        assert done.assigned_staff_id == suresh.id

    def test_removing_customer_from_route_unassigns(self, biz, suresh, plan):
        rahul, priya = customer(biz, "Rahul"), customer(biz, "Priya")
        subscribe(biz, plan, rahul)
        subscribe(biz, plan, priya)
        route = RouteService.save_route(
            business_id=biz.id, name="Kakkanad", staff=suresh, customer_ids=[rahul.id, priya.id]
        )
        RouteService.save_route(
            business_id=biz.id, route=route, name="Kakkanad", staff=suresh, customer_ids=[rahul.id]
        )
        assert staff_of(rahul) == {suresh.id}
        assert staff_of(priya) == {None}
        priya.refresh_from_db()
        assert priya.route_id is None

    def test_deleting_route_unassigns(self, biz, suresh, plan):
        cust = customer(biz, "Rahul")
        subscribe(biz, plan, cust)
        route = RouteService.save_route(
            business_id=biz.id, name="Kakkanad", staff=suresh, customer_ids=[cust.id]
        )
        RouteService.delete_route(route)
        assert staff_of(cust) == {None}

    def test_paused_then_resumed_meals_follow_new_staff(self, biz, suresh, anil, plan):
        cust = customer(biz, "Rahul")
        sub = subscribe(biz, plan, cust)
        route = RouteService.save_route(
            business_id=biz.id, name="Kakkanad", staff=suresh, customer_ids=[cust.id]
        )
        SubscriptionService.pause(sub)
        RouteService.save_route(business_id=biz.id, route=route, name="Kakkanad", staff=anil)
        SubscriptionService.resume(sub)
        pending = Delivery.objects.filter(subscription=sub, status=DeliveryStatus.PENDING)
        assert set(pending.values_list("assigned_staff_id", flat=True)) == {anil.id}

    def test_non_delivery_staff_rejected(self, biz, owner):
        with pytest.raises(ValueError):
            RouteService.save_route(business_id=biz.id, name="Kakkanad", staff=owner)

    def test_duplicate_name_rejected(self, biz, suresh):
        RouteService.save_route(business_id=biz.id, name="Kakkanad", staff=suresh)
        with pytest.raises(ValueError):
            RouteService.save_route(business_id=biz.id, name="kakkanad", staff=None)


@pytest.mark.django_db
class TestStaffView:
    def test_staff_sees_own_route_and_open_deliveries_only(self, biz, suresh, anil, plan):
        mine, theirs, open_ = customer(biz, "Mine"), customer(biz, "Theirs"), customer(biz, "Open")
        for c in (mine, theirs, open_):
            subscribe(biz, plan, c)
        RouteService.save_route(business_id=biz.id, name="A", staff=suresh, customer_ids=[mine.id])
        RouteService.save_route(business_id=biz.id, name="B", staff=anil, customer_ids=[theirs.id])

        names = {
            d["customer_name"] for d in client(suresh).get("/api/v1/deliveries/today/").json()["results"]
        }
        assert names == {"Mine", "Open"}

    def test_owner_filters_today_by_route(self, biz, owner, suresh, plan):
        mine, open_ = customer(biz, "Mine"), customer(biz, "Open")
        subscribe(biz, plan, mine)
        subscribe(biz, plan, open_)
        route = RouteService.save_route(business_id=biz.id, name="A", staff=suresh, customer_ids=[mine.id])
        c = client(owner)
        rows = c.get("/api/v1/deliveries/today/", {"route": str(route.id)}).json()["results"]
        assert [(r["customer_name"], r["route_name"]) for r in rows] == [("Mine", "A")]
        rows = c.get("/api/v1/deliveries/today/", {"no_route": "true"}).json()["results"]
        assert [r["customer_name"] for r in rows] == ["Open"]

    def test_deactivated_staff_hands_back_route(self, biz, owner, suresh, plan):
        cust = customer(biz, "Rahul")
        subscribe(biz, plan, cust)
        route = RouteService.save_route(business_id=biz.id, name="A", staff=suresh, customer_ids=[cust.id])
        assert client(owner).post(f"/api/v1/staff/{suresh.id}/deactivate/").status_code == 200
        route.refresh_from_db()
        assert route.staff_id is None
        assert staff_of(cust) == {None}

    def test_role_change_hands_back_route(self, biz, owner, suresh, plan):
        cust = customer(biz, "Rahul")
        subscribe(biz, plan, cust)
        RouteService.save_route(business_id=biz.id, name="A", staff=suresh, customer_ids=[cust.id])
        resp = client(owner).patch(f"/api/v1/staff/{suresh.id}/", {"role": Role.KITCHEN_STAFF}, format="json")
        assert resp.status_code == 200
        assert staff_of(cust) == {None}


@pytest.mark.django_db
class TestRouteApi:
    def test_create_with_customers(self, biz, owner, suresh, plan):
        cust = customer(biz, "Rahul")
        subscribe(biz, plan, cust)
        resp = client(owner).post(
            ROUTES,
            {"name": "Kakkanad", "staff": str(suresh.id), "customer_ids": [str(cust.id)]},
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["staff_name"] == "Suresh"
        assert body["customer_count"] == 1
        assert [c["name"] for c in body["customers"]] == ["Rahul"]
        assert staff_of(cust) == {suresh.id}

    def test_patch_staff_and_list(self, biz, owner, suresh, anil):
        c = client(owner)
        route_id = c.post(ROUTES, {"name": "Kakkanad", "staff": str(suresh.id)}, format="json").json()["id"]
        resp = c.patch(f"{ROUTES}{route_id}/", {"staff": str(anil.id)}, format="json")
        assert resp.status_code == 200
        assert resp.json()["staff_name"] == "Anil"
        assert [r["name"] for r in c.get(ROUTES).json()] == ["Kakkanad"]

    def test_delete(self, biz, owner):
        c = client(owner)
        route_id = c.post(ROUTES, {"name": "Kakkanad"}, format="json").json()["id"]
        assert c.delete(f"{ROUTES}{route_id}/").status_code == 204
        assert not DeliveryRoute.objects.exists()

    def test_bad_staff_is_validation_error(self, biz, owner):
        resp = client(owner).post(ROUTES, {"name": "Kakkanad", "staff": str(owner.id)}, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_feature_off_is_forbidden(self, biz, owner):
        FeatureService.set_overrides(biz.id, {DELIVERY_ROUTES: False})
        assert client(owner).get(ROUTES).status_code == 403

    def test_delivery_staff_cannot_manage_routes(self, suresh):
        assert client(suresh).get(ROUTES).status_code == 403

    def test_customer_route_set_via_customer_api(self, biz, owner, suresh, plan):
        cust = customer(biz, "Rahul")
        subscribe(biz, plan, cust)
        route = RouteService.save_route(business_id=biz.id, name="A", staff=suresh)
        resp = client(owner).patch(f"/api/v1/customers/{cust.id}/", {"route": str(route.id)}, format="json")
        assert resp.status_code == 200, resp.json()
        assert staff_of(cust) == {suresh.id}
        detail = client(owner).get(f"/api/v1/customers/{cust.id}/").json()
        assert detail["route_name"] == "A"


@pytest.mark.django_db
class TestIsolation:
    def test_other_business_route_is_404(self, other_biz, owner):
        other_route = RouteService.save_route(business_id=other_biz.id, name="Theirs", staff=None)
        c = client(owner)
        assert c.get(f"{ROUTES}{other_route.id}/").status_code == 404
        assert c.patch(f"{ROUTES}{other_route.id}/", {"name": "x"}, format="json").status_code == 404
        assert c.delete(f"{ROUTES}{other_route.id}/").status_code == 404
        assert c.get(ROUTES).json() == []

    def test_cannot_put_other_business_customer_on_route(self, biz, other_biz, owner):
        theirs = customer(other_biz, "Theirs")
        resp = client(owner).post(ROUTES, {"name": "A", "customer_ids": [str(theirs.id)]}, format="json")
        assert resp.status_code == 400
        theirs.refresh_from_db()
        assert theirs.route_id is None

    def test_cannot_assign_other_business_staff(self, biz, other_biz, owner):
        their_rider = rider(other_biz, "outsider")
        resp = client(owner).post(ROUTES, {"name": "A", "staff": str(their_rider.id)}, format="json")
        assert resp.status_code == 400

    def test_cannot_set_customer_to_other_business_route(self, biz, other_biz, owner):
        other_route = RouteService.save_route(business_id=other_biz.id, name="Theirs", staff=None)
        cust = customer(biz, "Rahul")
        resp = client(owner).patch(
            f"/api/v1/customers/{cust.id}/", {"route": str(other_route.id)}, format="json"
        )
        assert resp.status_code == 400
