"""Per-customer subscriptions (feature ``custom_subscriptions``): a custom price and food
extras (e.g. "+100g chicken", ₹20 per meal). Covers payment math, the activation chain,
mid-subscription changes, renewal, kitchen counts, feature gating and tenant isolation."""

import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from apps.customization.registry import CUSTOM_SUBSCRIPTIONS
from apps.customization.services import FeatureService
from apps.deliveries.models import Delivery
from apps.deliveries.services import DeliverySelector
from apps.meals.models import Meal
from apps.payments.services import PaymentService
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription
from apps.subscriptions.services import SubscriptionService
from common.constants import Role, SubStatus

TODAY = datetime.date.today()
SUBS = "/api/v1/subscriptions/"
CHICKEN = {"label": "Extra chicken 100g", "price_per_meal": "20.00"}
NO_RICE = {"label": "No rice", "price_per_meal": "0"}


def client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture()
def biz(db):
    b = Business.objects.create(name="Custom Mess")
    FeatureService.set_overrides(b.id, {CUSTOM_SUBSCRIPTIONS: True})
    return b


@pytest.fixture()
def owner(biz):
    return User.objects.create_user(username="owner", password="pass", role=Role.OWNER, business=biz)


@pytest.fixture()
def plan(biz):
    meal = Meal.objects.create(business=biz, name="Lunch")
    # 10 meals for ₹1000
    return Plan.objects.create(
        business=biz,
        name="Ten Lunches",
        meal=meal,
        duration_days=10,
        total_meals=10,
        price=Decimal("1000.00"),
    )


@pytest.fixture()
def cust(biz):
    return Customer.objects.create(business=biz, name="Rahul", phone="9000000001")


def create(biz, plan, cust, **kw):
    return SubscriptionService.create_subscription(
        business_id=biz.id, customer=cust, plan=plan, start_date=TODAY, **kw
    )


def pay(sub, amount):
    PaymentService.record_payment(
        business_id=sub.business_id,
        subscription=sub,
        amount=Decimal(amount),
        method="CASH",
        payment_date=TODAY,
    )
    sub.refresh_from_db()


def labels(sub):
    return [i.label for i in sub.items.all()]


@pytest.mark.django_db
class TestPricing:
    def test_extras_are_charged_per_meal(self, biz, plan, cust):
        sub = create(biz, plan, cust, items=[CHICKEN, NO_RICE])
        assert sub.total_amount == Decimal("1200.00")  # 1000 + 20 × 10
        assert sub.pending_amount == Decimal("1200.00")
        assert labels(sub) == ["Extra chicken 100g", "No rice"]

    def test_custom_price_replaces_plan_price(self, biz, plan, cust):
        sub = create(biz, plan, cust, custom_price=Decimal("900.00"), items=[CHICKEN])
        assert sub.total_amount == Decimal("1100.00")
        assert sub.custom_price == Decimal("900.00")

    def test_no_customization_is_plan_price(self, biz, plan, cust):
        assert create(biz, plan, cust).total_amount == Decimal("1000.00")

    def test_blank_labels_dropped_and_negative_rejected(self, biz, plan, cust):
        sub = create(biz, plan, cust, items=[{"label": "  ", "price_per_meal": "5"}])
        assert labels(sub) == [] and sub.total_amount == Decimal("1000.00")
        with pytest.raises(ValueError):
            create(
                biz,
                plan,
                Customer.objects.create(business=biz, name="B", phone="2"),
                items=[{"label": "x", "price_per_meal": "-1"}],
            )

    def test_free_custom_price_activates_immediately(self, biz, plan, cust):
        sub = create(biz, plan, cust, custom_price=Decimal("0"))
        assert sub.status == SubStatus.ACTIVE
        assert Delivery.objects.filter(subscription=sub).count() == 10

    def test_full_payment_of_custom_total_activates(self, biz, plan, cust):
        sub = create(biz, plan, cust, items=[CHICKEN])
        pay(sub, "1000")
        assert sub.status == SubStatus.PENDING
        pay(sub, "200")
        assert sub.status == SubStatus.ACTIVE
        assert sub.pending_amount == 0


@pytest.mark.django_db
class TestCustomize:
    def test_pending_change_recomputes_total(self, biz, plan, cust):
        sub = create(biz, plan, cust)
        SubscriptionService.customize(sub, items=[CHICKEN], custom_price=Decimal("800"))
        assert sub.total_amount == Decimal("1000.00")  # 800 + 200
        assert sub.pending_amount == Decimal("1000.00")

    def test_pending_change_keeps_custom_price_when_omitted(self, biz, plan, cust):
        sub = create(biz, plan, cust, custom_price=Decimal("800"))
        SubscriptionService.customize(sub, items=[CHICKEN])
        assert sub.total_amount == Decimal("1000.00")

    def test_pending_change_covered_by_payment_activates(self, biz, plan, cust):
        sub = create(biz, plan, cust, items=[CHICKEN])
        pay(sub, "1000")
        SubscriptionService.customize(sub, items=[NO_RICE])  # drops the ₹200 extra
        sub.refresh_from_db()
        assert sub.status == SubStatus.ACTIVE
        assert sub.pending_amount == 0
        assert Delivery.objects.filter(subscription=sub).count() == 10

    def test_active_extra_charged_for_meals_left(self, biz, plan, cust):
        sub = create(biz, plan, cust)
        pay(sub, "1000")
        Subscription.objects.filter(pk=sub.pk).update(remaining_meals=4)
        sub.refresh_from_db()
        SubscriptionService.customize(sub, items=[CHICKEN])
        sub.refresh_from_db()
        assert sub.status == SubStatus.ACTIVE
        assert sub.total_amount == Decimal("1080.00")  # + 20 × 4 meals left
        assert sub.pending_amount == Decimal("80.00")
        pay(sub, "80")  # ACTIVE subscriptions accept the extra payment
        assert sub.pending_amount == 0

    def test_active_free_change_keeps_price(self, biz, plan, cust):
        sub = create(biz, plan, cust)
        pay(sub, "1000")
        SubscriptionService.customize(sub, items=[NO_RICE])
        sub.refresh_from_db()
        assert sub.total_amount == Decimal("1000.00") and labels(sub) == ["No rice"]

    def test_active_cannot_drop_below_paid(self, biz, plan, cust):
        sub = create(biz, plan, cust, items=[CHICKEN])
        pay(sub, "1200")
        with pytest.raises(ValueError, match="already paid"):
            SubscriptionService.customize(sub, items=[])
        sub.refresh_from_db()
        assert labels(sub) == ["Extra chicken 100g"]

    def test_active_price_change_rejected(self, biz, plan, cust):
        sub = create(biz, plan, cust)
        pay(sub, "1000")
        with pytest.raises(ValueError, match="before the subscription starts"):
            SubscriptionService.customize(sub, items=[], custom_price=Decimal("500"))

    @pytest.mark.parametrize("end_status", [SubStatus.CANCELLED, SubStatus.EXPIRED])
    def test_ended_subscription_rejected(self, biz, plan, cust, end_status):
        sub = create(biz, plan, cust)
        Subscription.objects.filter(pk=sub.pk).update(status=end_status)
        with pytest.raises(ValueError):
            SubscriptionService.customize(sub, items=[CHICKEN])


@pytest.mark.django_db
class TestRenewal:
    def test_renewal_keeps_custom_price_and_extras(self, biz, plan, cust):
        sub = create(biz, plan, cust, custom_price=Decimal("900"), items=[CHICKEN, NO_RICE])
        SubscriptionService.cancel(sub)
        renewal = SubscriptionService.renew(sub)
        assert renewal.custom_price == Decimal("900.00")
        assert renewal.total_amount == Decimal("1100.00")
        assert labels(renewal) == ["Extra chicken 100g", "No rice"]
        assert labels(sub) == ["Extra chicken 100g", "No rice"]  # old one untouched


@pytest.mark.django_db
class TestKitchenAndDelivery:
    @staticmethod
    def active(biz, plan, cust, items):
        sub = create(biz, plan, cust, items=items)
        pay(sub, str(sub.total_amount))
        assert sub.status == SubStatus.ACTIVE
        return sub

    def test_kitchen_counts_total_extras(self, biz, plan, owner):
        lists = [[CHICKEN, NO_RICE], [CHICKEN], [{"label": "extra  CHICKEN 100g"}], []]
        for i, items in enumerate(lists):
            self.active(biz, plan, Customer.objects.create(business=biz, name=f"C{i}", phone=f"90{i}"), items)
        counts = DeliverySelector.get_kitchen_counts(biz.id)
        assert counts == [
            {
                "meal_id": plan.meal_id,
                "meal__name": "Lunch",
                "count": 4,
                "extras": [{"label": "Extra chicken 100g", "count": 3}, {"label": "No rice", "count": 1}],
                # 3 customers × 100 g — "No rice" isn't food to cook.
                "extra_food": [
                    {
                        "food": "Chicken",
                        "unit": "g",
                        "total": 300.0,
                        "customers": 3,
                        "labels": ["Extra chicken 100g"],
                    }
                ],
            }
        ]
        api = client(owner).get("/api/v1/deliveries/kitchen_counts/").json()
        assert api == [{**counts[0], "meal_id": str(plan.meal_id)}]

    def test_kitchen_adds_up_same_food_in_different_amounts(self, biz, plan):
        lists = [[CHICKEN], [{"label": "Extra chicken 150g"}], [{"label": "Add 2 chapati"}], [CHICKEN]]
        for i, items in enumerate(lists):
            self.active(biz, plan, Customer.objects.create(business=biz, name=f"C{i}", phone=f"90{i}"), items)
        food = {
            f["food"]: (f["total"], f["unit"], f["customers"])
            for f in DeliverySelector.get_kitchen_counts(biz.id)[0]["extra_food"]
        }
        assert food == {"Chicken": (350.0, "g", 3), "Chapati": (2.0, "pcs", 1)}

    def test_delivery_shows_customizations(self, biz, plan, cust, owner):
        self.active(biz, plan, cust, [CHICKEN, NO_RICE])
        rows = client(owner).get("/api/v1/deliveries/today/").json()["results"]
        assert rows[0]["customizations"] == ["Extra chicken 100g", "No rice"]


@pytest.mark.django_db
class TestApi:
    def test_create_with_customization(self, owner, plan, cust):
        resp = client(owner).post(
            SUBS,
            {"customer": str(cust.id), "plan": str(plan.id), "custom_price": "900", "items": [CHICKEN]},
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["total_amount"] == "1100.00"
        assert body["custom_price"] == "900.00"
        assert body["items"] == [{"label": "Extra chicken 100g", "price_per_meal": "20.00"}]

    def test_customize_endpoint(self, biz, owner, plan, cust):
        sub = create(biz, plan, cust)
        resp = client(owner).post(f"{SUBS}{sub.id}/customize/", {"items": [CHICKEN]}, format="json")
        assert resp.status_code == 200, resp.json()
        assert resp.json()["total_amount"] == "1200.00"
        listed = client(owner).get(SUBS).json()["results"][0]
        assert listed["items"][0]["label"] == "Extra chicken 100g"

    def test_customize_error_is_validation_error(self, biz, owner, plan, cust):
        sub = create(biz, plan, cust)
        SubscriptionService.cancel(sub)
        resp = client(owner).post(f"{SUBS}{sub.id}/customize/", {"items": []}, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_feature_off_rejects_customization(self, biz, owner, plan, cust):
        FeatureService.set_overrides(biz.id, {CUSTOM_SUBSCRIPTIONS: False})
        c = client(owner)
        resp = c.post(
            SUBS, {"customer": str(cust.id), "plan": str(plan.id), "items": [CHICKEN]}, format="json"
        )
        assert resp.status_code == 400
        # plain subscriptions still work
        assert (
            c.post(SUBS, {"customer": str(cust.id), "plan": str(plan.id)}, format="json").status_code == 201
        )
        sub = Subscription.objects.get(customer=cust)
        assert c.post(f"{SUBS}{sub.id}/customize/", {"items": []}, format="json").status_code == 403

    def test_delivery_staff_cannot_customize(self, biz, plan, cust):
        rider = User.objects.create_user(username="r", password="p", role=Role.DELIVERY_STAFF, business=biz)
        sub = create(biz, plan, cust)
        assert (
            client(rider).post(f"{SUBS}{sub.id}/customize/", {"items": []}, format="json").status_code == 403
        )

    def test_other_business_subscription_is_404(self, biz, plan, cust):
        other = Business.objects.create(name="Other")
        FeatureService.set_overrides(other.id, {CUSTOM_SUBSCRIPTIONS: True})
        outsider = User.objects.create_user(username="o", password="p", role=Role.OWNER, business=other)
        sub = create(biz, plan, cust)
        resp = client(outsider).post(f"{SUBS}{sub.id}/customize/", {"items": [CHICKEN]}, format="json")
        assert resp.status_code == 404
        assert labels(sub) == []


@pytest.mark.django_db
class TestPortal:
    def test_customer_sees_own_customizations(self, biz, plan, cust):
        from apps.customization.registry import CUSTOMER_PORTAL

        FeatureService.set_overrides(biz.id, {CUSTOMER_PORTAL: True})
        login = User.objects.create_user(username="rahul", password="p", role=Role.CUSTOMER, business=biz)
        cust.user = login
        cust.save()
        sub = create(biz, plan, cust, items=[CHICKEN])
        pay(sub, "1200")
        c = client(login)
        subs = c.get("/api/v1/portal/subscriptions/").json()
        assert subs[0]["items"] == [{"label": "Extra chicken 100g", "price_per_meal": "20.00"}]
        dash = c.get("/api/v1/portal/dashboard/").json()
        assert dash["active_subscription"]["items"][0]["label"] == "Extra chicken 100g"
        deliveries = c.get("/api/v1/portal/deliveries/").json()
        assert deliveries[0]["customizations"] == ["Extra chicken 100g"]


@pytest.mark.django_db
class TestKitchenMealDrillDown:
    URL = "/api/v1/deliveries/kitchen_meal/"

    def test_lists_customers_with_their_customizations(self, biz, plan, owner):
        a = Customer.objects.create(
            business=biz, name="Bina", phone="901", address="Flat 1", location="Room 12"
        )
        b = Customer.objects.create(business=biz, name="Arun", phone="902")
        TestKitchenAndDelivery.active(biz, plan, a, [CHICKEN, NO_RICE])
        TestKitchenAndDelivery.active(biz, plan, b, [])
        kitchen = User.objects.create_user(username="k", password="p", role=Role.KITCHEN_STAFF, business=biz)

        data = client(kitchen).get(self.URL, {"meal": str(plan.meal_id)}).json()
        assert data["meal_name"] == "Lunch"
        assert data["count"] == 2
        assert [c["name"] for c in data["customers"]] == ["Arun", "Bina"]
        bina = data["customers"][1]
        assert bina["customizations"] == ["Extra chicken 100g", "No rice"]
        assert bina["location"] == "Room 12"
        assert "phone" not in bina and "address" not in bina  # kitchen needs names, not contact details
        assert data["extra_food"][0]["food"] == "Chicken"
        assert data["extra_food"][0]["total"] == 100.0

    def test_delivered_plates_drop_off(self, biz, plan, cust, owner):
        TestKitchenAndDelivery.active(biz, plan, cust, [])
        Delivery.objects.filter(subscription__customer=cust).update(status="DELIVERED")
        data = client(owner).get(self.URL, {"meal": str(plan.meal_id)}).json()
        assert data["count"] == 0

    def test_other_business_meal_is_404(self, biz, plan, cust):
        TestKitchenAndDelivery.active(biz, plan, cust, [CHICKEN])
        other = Business.objects.create(name="Other")
        owner_b = User.objects.create_user(username="ob", password="p", role=Role.OWNER, business=other)
        resp = client(owner_b).get(self.URL, {"meal": str(plan.meal_id)})
        assert resp.status_code == 404

    def test_bad_meal_id_is_400(self, owner):
        assert client(owner).get(self.URL, {"meal": "nope"}).status_code == 400

    def test_delivery_staff_cannot_see_kitchen_list(self, biz, plan):
        staff = User.objects.create_user(username="d", password="p", role=Role.DELIVERY_STAFF, business=biz)
        assert client(staff).get(self.URL, {"meal": str(plan.meal_id)}).status_code == 403
