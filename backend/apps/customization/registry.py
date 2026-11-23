"""What can differ between messes — the single catalog, defined in code.

Two kinds of customization, both chosen per business by SUPER_ADMIN:

- **Features**: modules a mess has or doesn't have. A business gets its SaaS
  plan's feature list (or every default feature when the plan doesn't set one),
  then per-business overrides on top.
- **Extension points**: named steps of a workflow whose behaviour varies. Each
  point has registered policies; a business picks one (plus its params), or
  gets the point's default.

Rule: never branch on a specific business in code. A new variation is a new
feature key or a new registered policy, available to every mess.
"""

from dataclasses import dataclass

# ── Features ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Feature:
    key: str
    label: str
    description: str
    default: bool = True  # on for businesses whose plan doesn't list features


CUSTOMER_PORTAL = "customer_portal"
ONLINE_PAYMENTS = "online_payments"
REPORTS = "reports"
CUSTOM_SUBSCRIPTIONS = "custom_subscriptions"
DELIVERY_ROUTES = "delivery_routes"

FEATURES = {
    f.key: f
    for f in [
        Feature(CUSTOMER_PORTAL, "Customer portal", "Customers log in to see meals, pay, skip and pause."),
        Feature(ONLINE_PAYMENTS, "Online payments", "Customers pay through the business's Razorpay account."),
        Feature(REPORTS, "Reports", "Customer, subscription, revenue, meal and payment reports."),
        Feature(
            CUSTOM_SUBSCRIPTIONS,
            "Custom subscriptions",
            "Per-customer price and food extras (e.g. +100g chicken) on a subscription; "
            "the kitchen sees the extras in today's counts.",
            default=False,
        ),
        Feature(
            DELIVERY_ROUTES,
            "Delivery routes",
            "Group customers into routes, each run by one delivery staff member who sees only "
            "their route's deliveries.",
            default=False,
        ),
    ]
}

DEFAULT_FEATURES = frozenset(k for k, f in FEATURES.items() if f.default)


# ── Extension points & policies ────────────────────────────────────────


class Policy:
    """One way of doing a workflow step. Subclass per variant and register it.

    ``params_serializer`` (a DRF Serializer class) validates the per-business
    params; leave it None for a policy without params.
    """

    key = ""
    label = ""
    description = ""
    params_serializer = None

    def __init__(self, **params):
        self.params = params


class ExtensionPoint:
    def __init__(self, key, label, description, default):
        self.key = key
        self.label = label
        self.description = description
        self.default = default
        self.policies = {}

    def register(self, policy_cls):
        """Class decorator: make ``policy_cls`` selectable for this point."""
        if policy_cls.key in self.policies:
            raise ValueError(f"{self.key}: policy {policy_cls.key!r} registered twice")
        self.policies[policy_cls.key] = policy_cls
        return policy_cls

    def validate_params(self, policy_key, params):
        """Return cleaned params for ``policy_key``; raise ValueError/ValidationError if bad."""
        policy_cls = self.policies.get(policy_key)
        if policy_cls is None:
            raise ValueError(f"Unknown {self.key} policy {policy_key!r}.")
        if policy_cls.params_serializer is None:
            return {}
        serializer = policy_cls.params_serializer(data=params or {})
        serializer.is_valid(raise_exception=True)
        return dict(serializer.validated_data)

    def build(self, policy_key=None, params=None):
        """Instantiate the chosen policy, falling back to the default if it was unregistered."""
        if policy_key in self.policies:
            return self.policies[policy_key](**(params or {}))
        return self.policies[self.default]()


SKIP = "skip"

EXTENSION_POINTS = {
    p.key: p
    for p in [
        ExtensionPoint(SKIP, "Meal skip", "What happens to the subscription when a meal is skipped.", "NONE"),
    ]
}


def extension_point(key):
    return EXTENSION_POINTS[key]
