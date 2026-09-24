"""Shared constants."""

from types import SimpleNamespace

Role = SimpleNamespace(
    SUPER_ADMIN="SUPER_ADMIN",
    OWNER="OWNER",
    MANAGER="MANAGER",
    DELIVERY_STAFF="DELIVERY_STAFF",
    KITCHEN_STAFF="KITCHEN_STAFF",
    CUSTOMER="CUSTOMER",
)

ROLE_CHOICES = [
    (Role.SUPER_ADMIN, "Super Admin"),
    (Role.OWNER, "Owner"),
    (Role.MANAGER, "Manager"),
    (Role.DELIVERY_STAFF, "Delivery Staff"),
    (Role.KITCHEN_STAFF, "Kitchen Staff"),
    (Role.CUSTOMER, "Customer"),
]

# Roles that operate a business (everyone who is not platform-level or a customer)
BUSINESS_STAFF_ROLES = [Role.OWNER, Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF]

Status = SimpleNamespace(
    ACTIVE="ACTIVE",
    INACTIVE="INACTIVE",
    SUSPENDED="SUSPENDED",
    BLOCKED="BLOCKED",
)
