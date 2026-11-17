"""Resolve and change what a business gets. Other modules only call these."""

from django.db import transaction

from apps.customization.models import BusinessFeature, BusinessPolicy
from apps.customization.registry import DEFAULT_FEATURES, EXTENSION_POINTS, FEATURES, extension_point


def _plan_features(business_id):
    """The SaaS plan's feature keys, or None when the plan doesn't restrict features."""
    from apps.platform.models import SaasSubscription

    sub = SaasSubscription.objects.select_related("plan").filter(business_id=business_id).first()
    if sub is None or sub.plan is None:
        return None
    return sub.plan.feature_keys


class FeatureService:
    @staticmethod
    def inherited(business_id):
        """(feature keys, source) the business gets before its overrides; source is plan | default."""
        plan_keys = _plan_features(business_id)
        if plan_keys is None:
            return DEFAULT_FEATURES, "default"
        return frozenset(plan_keys), "plan"

    @staticmethod
    def resolve(business_id):
        """{key: (enabled, source)} for every feature; source is plan | override | default."""
        base, base_source = FeatureService.inherited(business_id)
        result = {key: (key in base, base_source) for key in FEATURES}
        for key, enabled in BusinessFeature.objects.filter(business_id=business_id).values_list(
            "key", "enabled"
        ):
            if key in result:
                result[key] = (enabled, "override")
        return result

    @staticmethod
    def enabled(business_id):
        """Set of feature keys the business has."""
        if business_id is None:
            return set()
        return {key for key, (on, _src) in FeatureService.resolve(business_id).items() if on}

    @staticmethod
    def has(business_id, key):
        return key in FeatureService.enabled(business_id)

    @staticmethod
    @transaction.atomic
    def set_overrides(business_id, overrides):
        """``overrides`` = {key: True | False | None}; None removes the override."""
        for key, enabled in overrides.items():
            if key not in FEATURES:
                raise ValueError(f"Unknown feature {key!r}.")
            if enabled is None:
                BusinessFeature.objects.filter(business_id=business_id, key=key).delete()
            else:
                BusinessFeature.objects.update_or_create(
                    business_id=business_id, key=key, defaults={"enabled": enabled}
                )


class PolicyService:
    @staticmethod
    def get(business_id, point):
        """The policy instance this business uses at ``point``."""
        row = BusinessPolicy.objects.filter(business_id=business_id, point=point).first()
        if row is None:
            return extension_point(point).build()
        return extension_point(point).build(row.policy, row.params)

    @staticmethod
    def selected(business_id):
        """{point: (policy_key, params)} for every extension point, defaults filled in."""
        rows = {
            r.point: r
            for r in BusinessPolicy.objects.filter(business_id=business_id)
            if r.point in EXTENSION_POINTS and r.policy in EXTENSION_POINTS[r.point].policies
        }
        return {
            key: (rows[key].policy, rows[key].params) if key in rows else (point.default, {})
            for key, point in EXTENSION_POINTS.items()
        }

    @staticmethod
    @transaction.atomic
    def set_policy(business_id, point, policy_key, params=None):
        """Choose ``policy_key`` for ``point``. Picking the default removes the row."""
        if point not in EXTENSION_POINTS:
            raise ValueError(f"Unknown extension point {point!r}.")
        ext = extension_point(point)
        cleaned = ext.validate_params(policy_key, params)
        if policy_key == ext.default and not cleaned:
            BusinessPolicy.objects.filter(business_id=business_id, point=point).delete()
            return
        BusinessPolicy.objects.update_or_create(
            business_id=business_id, point=point, defaults={"policy": policy_key, "params": cleaned}
        )
