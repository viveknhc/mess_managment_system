"""Forgot password — request a link by username/email, set a new password with it."""

import re
from unittest import mock

import pytest
from django.core import mail
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.accounts.views import RESET_REQUESTED_MESSAGE
from apps.businesses.models import Business
from common.constants import Role

REQUEST_URL = "/api/v1/auth/password-reset/"
CONFIRM_URL = "/api/v1/auth/password-reset/confirm/"
NEW_PASSWORD = "Fresh-Pass-2026"


@pytest.fixture()
def biz(db):
    return Business.objects.create(name="Reset Mess")


@pytest.fixture()
def owner(biz):
    return User.objects.create_user(
        username="reset_owner",
        password="Old-Pass-2026",
        role=Role.OWNER,
        business=biz,
        email="owner@example.com",
    )


def _request(identifier):
    return APIClient().post(REQUEST_URL, {"identifier": identifier}, format="json")


def _link_params(message):
    uid, token = re.search(r"/reset-password\?uid=([^&\s]+)&token=(\S+)", message.body).groups()
    return {"uid": uid, "token": token}


def _confirm(params, password=NEW_PASSWORD):
    return APIClient().post(CONFIRM_URL, {**params, "new_password": password}, format="json")


class TestRequestReset:
    @pytest.mark.parametrize(
        "identifier", ["reset_owner", "RESET_OWNER", "owner@example.com", " Owner@Example.com "]
    )
    def test_sends_link_by_username_or_email(self, owner, identifier):
        resp = _request(identifier)
        assert resp.status_code == 200
        assert resp.json()["detail"] == RESET_REQUESTED_MESSAGE
        assert len(mail.outbox) == 1
        msg = mail.outbox[0]
        assert msg.to == ["owner@example.com"]
        assert "Username: reset_owner" in msg.body
        assert "Reset Mess" in msg.body

    @override_settings(FRONTEND_URL="https://app.messdeck.in")
    def test_link_points_at_frontend(self, owner):
        _request("reset_owner")
        assert "https://app.messdeck.in/reset-password?uid=" in mail.outbox[0].body

    def test_unknown_account_same_response_no_email(self, db):
        resp = _request("nobody")
        assert resp.status_code == 200
        assert resp.json()["detail"] == RESET_REQUESTED_MESSAGE
        assert mail.outbox == []

    def test_account_without_email_gets_nothing(self, biz):
        User.objects.create_user(username="no_mail", password="x", role=Role.DELIVERY_STAFF, business=biz)
        assert _request("no_mail").status_code == 200
        assert mail.outbox == []

    def test_inactive_account_gets_nothing(self, owner):
        owner.is_active = False
        owner.save()
        _request("reset_owner")
        assert mail.outbox == []

    def test_shared_email_each_account_gets_its_own_link(self, owner, biz):
        other = Business.objects.create(name="Second Mess")
        User.objects.create_user(
            username="cust_two", password="x", role=Role.CUSTOMER, business=other, email="owner@example.com"
        )
        _request("owner@example.com")
        assert sorted(re.search(r"Username: (\S+)", m.body).group(1) for m in mail.outbox) == [
            "cust_two",
            "reset_owner",
        ]

    def test_works_for_every_role(self, biz):
        for role in [Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF, Role.CUSTOMER, Role.SUPER_ADMIN]:
            User.objects.create_user(
                username=f"u_{role}",
                password="x",
                role=role,
                business=None if role == Role.SUPER_ADMIN else biz,
                email=f"{role}@example.com",
            )
            _request(f"u_{role}")
        assert len(mail.outbox) == 5

    def test_email_failure_doesnt_change_response(self, owner):
        with mock.patch("apps.accounts.services.send_mail", side_effect=OSError("smtp down")):
            resp = _request("reset_owner")
        assert resp.status_code == 200
        assert resp.json()["detail"] == RESET_REQUESTED_MESSAGE

    def test_blank_identifier_400(self, db):
        assert _request("").status_code == 400


class TestConfirmReset:
    def test_sets_new_password(self, owner):
        _request("reset_owner")
        resp = _confirm(_link_params(mail.outbox[0]))
        assert resp.status_code == 200
        owner.refresh_from_db()
        assert owner.check_password(NEW_PASSWORD)
        login = APIClient().post(
            "/api/v1/auth/login/", {"username": "reset_owner", "password": NEW_PASSWORD}, format="json"
        )
        assert login.status_code == 200

    def test_link_works_only_once(self, owner):
        _request("reset_owner")
        params = _link_params(mail.outbox[0])
        assert _confirm(params).status_code == 200
        resp = _confirm(params, "Another-Pass-2026")
        assert resp.status_code == 400
        assert "invalid or has expired" in resp.json()["error"]["message"]

    def test_expired_link_rejected(self, owner):
        _request("reset_owner")
        params = _link_params(mail.outbox[0])
        with override_settings(PASSWORD_RESET_TIMEOUT=-1):
            assert _confirm(params).status_code == 400

    def test_tampered_token_rejected(self, owner):
        _request("reset_owner")
        params = _link_params(mail.outbox[0])
        assert _confirm({**params, "token": params["token"][:-1] + "x"}).status_code == 400
        assert _confirm({**params, "uid": "bm90LWEtdXVpZA"}).status_code == 400
        assert _confirm({**params, "uid": "!!!"}).status_code == 400

    def test_weak_password_rejected_and_link_still_usable(self, owner):
        _request("reset_owner")
        params = _link_params(mail.outbox[0])
        resp = _confirm(params, "123")
        assert resp.status_code == 400
        assert "new_password" in resp.json()["error"]["fields"]
        assert _confirm(params).status_code == 200

    def test_signs_out_everywhere(self, owner):
        refresh = str(RefreshToken.for_user(owner))
        _request("reset_owner")
        _confirm(_link_params(mail.outbox[0]))
        resp = APIClient().post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json")
        assert resp.status_code == 401

    def test_deactivated_after_request_rejected(self, owner):
        _request("reset_owner")
        owner.is_active = False
        owner.save()
        assert _confirm(_link_params(mail.outbox[0])).status_code == 400
