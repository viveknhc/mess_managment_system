"""Tests for the common/ foundation (F-09..F-11).

Tenant-scoped create/query behaviors get full route-based coverage in Module 1
once auth URLs and factories exist; here we test the pieces that stand alone.
"""
import pytest
from rest_framework.test import APIClient

from common.constants import Role
from common.permissions import RoleBasedPermission


@pytest.mark.django_db
class TestErrorEnvelope:
    def test_auth_error_uses_envelope(self, db):
        api = APIClient()
        resp = api.get("/api/v1/business/")
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "AUTH_INVALID"
        assert "message" in body["error"]
        assert "fields" in body["error"]


class _View:
    """Bare view double for RoleBasedPermission tests."""

    def __init__(self, action="list", role_map=None, read_roles=None):
        self.action = action
        self.role_map = role_map or {}
        if read_roles:
            self.read_roles = read_roles


class _User:
    def __init__(self, role):
        self.role = role


@pytest.mark.django_db
class TestRoleBasedPermission:
    def test_unmapped_view_defaults_to_owner_manager(self):
        perm = RoleBasedPermission()
        req = type("R", (), {"user": _User(Role.OWNER), "method": "GET"})()
        assert perm.has_permission(req, _View()) is True

        req_customer = type("R", (), {"user": _User(Role.CUSTOMER), "method": "GET"})()
        assert perm.has_permission(req_customer, _View()) is False

    def test_role_map_allows_listed_role(self):
        perm = RoleBasedPermission()
        view = _View(action="update", role_map={"update": [Role.MANAGER, Role.OWNER]})
        req = type("R", (), {"user": _User(Role.MANAGER), "method": "PATCH"})()
        assert perm.has_permission(req, view) is True

    def test_role_map_blocks_unlisted_role(self):
        perm = RoleBasedPermission()
        view = _View(action="update", role_map={"update": [Role.OWNER]})
        req = type("R", (), {"user": _User(Role.DELIVERY_STAFF), "method": "PATCH"})()
        assert perm.has_permission(req, view) is False

    def test_read_roles_fallback_for_safe_methods(self):
        perm = RoleBasedPermission()
        view = _View(action="list", role_map={"list": [Role.OWNER]}, read_roles=[Role.DELIVERY_STAFF])
        req = type("R", (), {"user": _User(Role.DELIVERY_STAFF), "method": "GET"})()
        assert perm.has_permission(req, view) is True
