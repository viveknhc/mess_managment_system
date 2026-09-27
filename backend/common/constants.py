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

# ── Subscription state machine (S-03) ────────────────────────────────────

SubStatus = SimpleNamespace(
    PENDING="PENDING",
    ACTIVE="ACTIVE",
    PAUSED="PAUSED",
    EXPIRED="EXPIRED",
    CANCELLED="CANCELLED",
)

SUB_STATUS_CHOICES = [
    (SubStatus.PENDING, "Pending"),
    (SubStatus.ACTIVE, "Active"),
    (SubStatus.PAUSED, "Paused"),
    (SubStatus.EXPIRED, "Expired"),
    (SubStatus.CANCELLED, "Cancelled"),
]

# Legal transitions: {from_status: [to_statuses]}
SUB_TRANSITIONS = {
    SubStatus.PENDING: [SubStatus.ACTIVE, SubStatus.CANCELLED],
    SubStatus.ACTIVE: [SubStatus.PAUSED, SubStatus.CANCELLED, SubStatus.EXPIRED],
    SubStatus.PAUSED: [SubStatus.ACTIVE],
    SubStatus.EXPIRED: [],  # terminal — renew creates a new row
    SubStatus.CANCELLED: [],  # terminal
}
