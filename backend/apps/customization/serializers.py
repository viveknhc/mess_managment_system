"""Customization API shapes — the catalog and one business's choices."""

from rest_framework import serializers

from apps.customization.registry import EXTENSION_POINTS, FEATURES


def _params_fields(policy_cls):
    """Describe a policy's params for the admin form: [{name, type, label, required, default}]."""
    if policy_cls.params_serializer is None:
        return []
    out = []
    for name, field in policy_cls.params_serializer().fields.items():
        out.append(
            {
                "name": name,
                "type": type(field).__name__.removesuffix("Field").lower(),
                "label": field.label or name,
                "required": field.required,
                "default": None if field.default is serializers.empty else field.default,
            }
        )
    return out


def catalog_data():
    return {
        "features": [
            {"key": f.key, "label": f.label, "description": f.description, "default": f.default}
            for f in FEATURES.values()
        ],
        "extension_points": [
            {
                "key": p.key,
                "label": p.label,
                "description": p.description,
                "default": p.default,
                "policies": [
                    {
                        "key": cls.key,
                        "label": cls.label,
                        "description": cls.description,
                        "params": _params_fields(cls),
                    }
                    for cls in p.policies.values()
                ],
            }
            for p in EXTENSION_POINTS.values()
        ],
    }


def business_customization_data(resolved_features, inherited_features, selected_policies):
    """``inherited`` = what the feature would be without this business's override."""
    return {
        "features": [
            {"key": key, "enabled": enabled, "source": source, "inherited": key in inherited_features}
            for key, (enabled, source) in resolved_features.items()
        ],
        "policies": [
            {"point": point, "policy": key, "params": params}
            for point, (key, params) in selected_policies.items()
        ],
    }


class PolicyChoiceSerializer(serializers.Serializer):
    policy = serializers.CharField(max_length=50)
    params = serializers.DictField(required=False, default=dict)


class BusinessCustomizationUpdateSerializer(serializers.Serializer):
    """PUT body. features: {key: true | false | null (back to plan)}; policies: {point: {policy, params}}."""

    features = serializers.DictField(child=serializers.BooleanField(allow_null=True), required=False)
    policies = serializers.DictField(child=PolicyChoiceSerializer(), required=False)

    def validate_features(self, value):
        unknown = sorted(set(value) - set(FEATURES))
        if unknown:
            raise serializers.ValidationError(f"Unknown feature(s): {', '.join(unknown)}.")
        return value

    def validate_policies(self, value):
        for point, choice in value.items():
            ext = EXTENSION_POINTS.get(point)
            if ext is None:
                raise serializers.ValidationError(f"Unknown extension point {point!r}.")
            if choice["policy"] not in ext.policies:
                raise serializers.ValidationError({point: f"Unknown policy {choice['policy']!r}."})
            try:
                choice["params"] = ext.validate_params(choice["policy"], choice.get("params"))
            except serializers.ValidationError as e:
                problems = "; ".join(f"{name}: {' '.join(map(str, errs))}" for name, errs in e.detail.items())
                raise serializers.ValidationError({point: f"Invalid settings — {problems}"}) from e
        return value


def validate_feature_keys(value):
    """For SaasPlan.feature_keys — null or a list of known keys."""
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(k, str) for k in value):
        raise serializers.ValidationError("Must be a list of feature keys.")
    unknown = sorted(set(value) - set(FEATURES))
    if unknown:
        raise serializers.ValidationError(f"Unknown feature(s): {', '.join(unknown)}.")
    return sorted(set(value))
