"""?ordering= support on list endpoints (data-table column sorting)."""

import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.meals.models import Meal
from apps.plans.models import Plan
from apps.subscriptions.services import SubscriptionService
from common.constants import Role


@pytest.fixture()
def biz(db):
    return Business.objects.create(name="Mess A")


@pytest.fixture()
def api(biz):
    owner = User.objects.create_user(username="owner", password="pass", role=Role.OWNER, business=biz)
    client = APIClient()
    client.force_authenticate(owner)
    return client


@pytest.fixture()
def customers(biz):
    return [
        Customer.objects.create(business=biz, name=name, status=status)
        for name, status in [("Charlie", "ACTIVE"), ("alice", "INACTIVE"), ("Bob", "ACTIVE")]
    ]


@pytest.fixture()
def plans(biz):
    meal = Meal.objects.create(business=biz, name="Lunch")
    return [
        Plan.objects.create(
            business=biz, name=name, meal=meal, duration_days=30, total_meals=30, price=Decimal(price)
        )
        for name, price in [("Mid", "2500.00"), ("Cheap", "999.00"), ("Premium", "10000.00")]
    ]


def names(resp, key="name"):
    assert resp.status_code == 200, resp.content
    return [row[key] for row in resp.json()["results"]]


def test_default_ordering_unchanged_without_param(api, customers):
    # Model Meta ordering is ["name"] (case-sensitive in the DB collation used by tests).
    assert names(api.get("/api/v1/customers/")) == list(
        Customer.objects.order_by("name").values_list("name", flat=True)
    )


def test_ordering_asc_and_desc(api, plans):
    assert names(api.get("/api/v1/plans/?ordering=price")) == ["Cheap", "Mid", "Premium"]
    assert names(api.get("/api/v1/plans/?ordering=-price")) == ["Premium", "Mid", "Cheap"]


def test_ordering_numeric_not_lexical(api, plans):
    # 10000 > 2500 numerically but "10000.00" < "2500.00" as strings.
    assert names(api.get("/api/v1/plans/?ordering=-price"))[0] == "Premium"


def test_ordering_on_related_field(api, biz, plans):
    cust_z = Customer.objects.create(business=biz, name="Zed")
    cust_a = Customer.objects.create(business=biz, name="Amy")
    today = datetime.date.today()
    for cust in (cust_z, cust_a):
        SubscriptionService.create_subscription(
            business_id=biz.id, customer=cust, plan=plans[0], start_date=today
        )

    resp = api.get("/api/v1/subscriptions/?ordering=customer__name")
    assert names(resp, "customer_name") == ["Amy", "Zed"]
    resp = api.get("/api/v1/subscriptions/?ordering=-customer__name")
    assert names(resp, "customer_name") == ["Zed", "Amy"]


def test_multi_field_ordering(api, customers):
    resp = api.get("/api/v1/customers/?ordering=status,-name")
    rows = [(r["status"], r["name"]) for r in resp.json()["results"]]
    assert rows == [("ACTIVE", "Charlie"), ("ACTIVE", "Bob"), ("INACTIVE", "alice")]


def test_unknown_field_is_ignored_not_500(api, customers):
    # Not in ordering_fields — computed properties / sensitive fields must not be sortable.
    for bad in ("remaining_days", "business__name", "user__password", "nonsense"):
        resp = api.get(f"/api/v1/customers/?ordering={bad}")
        assert resp.status_code == 200


def test_ordering_combines_with_filters(api, customers):
    resp = api.get("/api/v1/customers/?status=ACTIVE&ordering=-name")
    assert names(resp) == ["Charlie", "Bob"]


def test_ties_are_stable_across_pages(api, biz):
    # 30 customers sharing one status: page 1 + page 2 must cover every row exactly once.
    for i in range(30):
        Customer.objects.create(business=biz, name=f"C{i:02d}", status="ACTIVE")
    page1 = api.get("/api/v1/customers/?ordering=status&page=1").json()["results"]
    page2 = api.get("/api/v1/customers/?ordering=status&page=2").json()["results"]
    ids = [r["id"] for r in page1 + page2]
    assert len(ids) == 30
    assert len(set(ids)) == 30


def test_ordering_respects_tenant_isolation(api, customers):
    other = Business.objects.create(name="Mess B")
    Customer.objects.create(business=other, name="AAA other tenant")
    assert "AAA other tenant" not in names(api.get("/api/v1/customers/?ordering=name"))


def test_page_size_param(api, biz):
    for i in range(15):
        Customer.objects.create(business=biz, name=f"C{i:02d}")
    body = api.get("/api/v1/customers/?page_size=10").json()
    assert body["count"] == 15
    assert len(body["results"]) == 10
