"""Customer CSV import tests."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.customers.models import Customer
from common.constants import Role

IMPORT_URL = "/api/v1/customers/import/"
TEMPLATE_URL = "/api/v1/customers/import-template/"


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
def kitchen_a(biz_a):
    return User.objects.create_user(
        username="kitchen_a", password="pass", role=Role.KITCHEN_STAFF, business=biz_a
    )


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def upload(client, content, name="customers.csv"):
    if isinstance(content, str):
        content = content.encode("utf-8")
    f = SimpleUploadedFile(name, content, content_type="text/csv")
    return client.post(IMPORT_URL, {"file": f}, format="multipart")


class TestImportSuccess:
    def test_owner_imports(self, owner_a, biz_a):
        csv_text = (
            "Name,Mobile,Email,Address,Notes\nRavi,9000000001,ravi@x.com,Pune,veg\nSita,9000000002,,,\n"
        )
        resp = upload(auth_client(owner_a), csv_text)
        assert resp.status_code == 201, resp.data
        assert resp.data == {"created": 2}
        ravi = Customer.objects.get(phone="9000000001")
        assert ravi.name == "Ravi"
        assert ravi.email == "ravi@x.com"
        assert ravi.address == "Pune"
        assert ravi.notes == "veg"
        assert ravi.business_id == biz_a.id
        codes = sorted(Customer.objects.filter(business=biz_a).values_list("customer_code", flat=True))
        assert codes == ["CUST-0001", "CUST-0002"]

    def test_codes_continue_after_existing(self, owner_a, biz_a):
        Customer.objects.create(business=biz_a, name="Existing", phone="9111111111")
        resp = upload(auth_client(owner_a), "name,phone\nNew,9000000001\n")
        assert resp.status_code == 201
        assert Customer.objects.get(phone="9000000001").customer_code == "CUST-0002"

    def test_manager_can_import(self, manager_a):
        resp = upload(auth_client(manager_a), "name,phone\nA,9000000001\n")
        assert resp.status_code == 201

    def test_bom_and_case_insensitive_headers(self, owner_a):
        content = "﻿NAME, Phone Number \nRavi,9000000001\n".encode()
        resp = upload(auth_client(owner_a), content)
        assert resp.status_code == 201, resp.data
        assert Customer.objects.filter(name="Ravi", phone="9000000001").exists()

    def test_blank_lines_skipped(self, owner_a):
        resp = upload(auth_client(owner_a), "name,phone\nA,9000000001\n,\n\nB,9000000002\n")
        assert resp.status_code == 201
        assert resp.data["created"] == 2

    def test_exactly_100_rows_allowed(self, owner_a):
        rows = "".join(f"C{i},90000{i:05d}\n" for i in range(100))
        resp = upload(auth_client(owner_a), "name,phone\n" + rows)
        assert resp.status_code == 201
        assert resp.data["created"] == 100


class TestImportValidation:
    def test_more_than_100_rows_rejected(self, owner_a):
        rows = "".join(f"C{i},90000{i:05d}\n" for i in range(101))
        resp = upload(auth_client(owner_a), "name,phone\n" + rows)
        assert resp.status_code == 400
        assert resp.data["error"]["code"] == "VALIDATION_ERROR"
        assert "100" in resp.data["error"]["message"]
        assert Customer.objects.count() == 0

    def test_bad_row_creates_nothing(self, owner_a):
        csv_text = "name,phone,email\nGood,9000000001,\n,9000000002,\nBadEmail,9000000003,not-an-email\n"
        resp = upload(auth_client(owner_a), csv_text)
        assert resp.status_code == 400
        assert resp.data["error"]["code"] == "VALIDATION_ERROR"
        rows = resp.data["error"]["fields"]["rows"]
        assert [r["row"] for r in rows] == [3, 4]
        assert "name" in rows[0]["errors"]
        assert "email" in rows[1]["errors"]
        assert Customer.objects.count() == 0

    def test_missing_phone_value(self, owner_a):
        resp = upload(auth_client(owner_a), "name,phone\nA,\n")
        assert resp.status_code == 400
        assert resp.data["error"]["fields"]["rows"][0]["errors"]["phone"]

    def test_missing_required_column(self, owner_a):
        resp = upload(auth_client(owner_a), "name,email\nA,a@x.com\n")
        assert resp.status_code == 400
        assert "phone" in resp.data["error"]["message"]

    def test_duplicate_phone_in_file(self, owner_a):
        resp = upload(auth_client(owner_a), "name,phone\nA,9000000001\nB,9000000001\n")
        assert resp.status_code == 400
        rows = resp.data["error"]["fields"]["rows"]
        assert len(rows) == 1
        assert rows[0]["row"] == 3
        assert "Duplicate" in rows[0]["errors"]["phone"][0]
        assert Customer.objects.count() == 0

    def test_duplicate_against_existing_customer(self, owner_a, biz_a):
        Customer.objects.create(business=biz_a, name="Existing", phone="9000000001")
        resp = upload(auth_client(owner_a), "name,phone\nNew,9000000002\nDup,9000000001\n")
        assert resp.status_code == 400
        rows = resp.data["error"]["fields"]["rows"]
        assert rows[0]["row"] == 3
        assert "already exists" in rows[0]["errors"]["phone"][0]
        assert Customer.objects.filter(business=biz_a).count() == 1

    def test_no_file(self, owner_a):
        resp = auth_client(owner_a).post(IMPORT_URL, {}, format="multipart")
        assert resp.status_code == 400

    def test_empty_file(self, owner_a):
        resp = upload(auth_client(owner_a), "")
        assert resp.status_code == 400

    def test_header_only(self, owner_a):
        resp = upload(auth_client(owner_a), "name,phone\n")
        assert resp.status_code == 400

    def test_non_utf8_rejected(self, owner_a):
        resp = upload(auth_client(owner_a), "name,phone\nJos\xe9,9000000001\n".encode("latin-1"))
        assert resp.status_code == 400
        assert "UTF-8" in resp.data["error"]["message"]


class TestImportIsolation:
    def test_business_id_column_ignored(self, owner_a, biz_a, biz_b):
        csv_text = f"name,phone,business_id,business\nA,9000000001,{biz_b.id},{biz_b.id}\n"
        resp = upload(auth_client(owner_a), csv_text)
        assert resp.status_code == 201
        assert Customer.objects.get(phone="9000000001").business_id == biz_a.id
        assert not Customer.objects.filter(business=biz_b).exists()

    def test_phone_in_other_business_does_not_conflict(self, owner_a, biz_b):
        Customer.objects.create(business=biz_b, name="Other", phone="9000000001")
        resp = upload(auth_client(owner_a), "name,phone\nMine,9000000001\n")
        assert resp.status_code == 201


class TestImportPermissions:
    def test_delivery_staff_forbidden(self, delivery_a):
        resp = upload(auth_client(delivery_a), "name,phone\nA,9000000001\n")
        assert resp.status_code == 403
        assert Customer.objects.count() == 0

    def test_kitchen_staff_forbidden(self, kitchen_a):
        resp = upload(auth_client(kitchen_a), "name,phone\nA,9000000001\n")
        assert resp.status_code == 403

    def test_unauthenticated(self, db):
        resp = upload(APIClient(), "name,phone\nA,9000000001\n")
        assert resp.status_code == 401

    def test_template_forbidden_for_staff(self, delivery_a):
        assert auth_client(delivery_a).get(TEMPLATE_URL).status_code == 403


class TestImportQuota:
    def _plan(self, biz, max_customers):
        from apps.platform.models import SaasPlan, SaasSubscription

        plan = SaasPlan.objects.create(name="Small", price_monthly="100.00", max_customers=max_customers)
        SaasSubscription.objects.create(business=biz, plan=plan)

    def test_import_exceeding_quota_rejected(self, owner_a, biz_a):
        self._plan(biz_a, 2)
        Customer.objects.create(business=biz_a, name="Existing", phone="9111111111")
        resp = upload(auth_client(owner_a), "name,phone\nA,9000000001\nB,9000000002\n")
        assert resp.status_code == 402
        assert Customer.objects.filter(business=biz_a).count() == 1

    def test_unlimited_plan_allows(self, owner_a, biz_a):
        self._plan(biz_a, 0)
        resp = upload(auth_client(owner_a), "name,phone\nA,9000000001\nB,9000000002\n")
        assert resp.status_code == 201


class TestImportTemplate:
    def test_owner_downloads_template(self, owner_a):
        resp = auth_client(owner_a).get(TEMPLATE_URL)
        assert resp.status_code == 200
        assert resp["Content-Type"].startswith("text/csv")
        lines = resp.content.decode().splitlines()
        assert lines[0] == "name,phone,email,address,location,notes"
        assert len(lines) == 2

    def test_template_round_trips(self, owner_a):
        content = auth_client(owner_a).get(TEMPLATE_URL).content
        resp = upload(auth_client(owner_a), content)
        assert resp.status_code == 201
