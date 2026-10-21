"""Shared DRF filter backends."""

from rest_framework.filters import OrderingFilter


class StableOrderingFilter(OrderingFilter):
    """`?ordering=field,-other` for list endpoints (data-table column sorting).

    - Opt-in: a view is sortable only on its explicit `ordering_fields`. DRF's
      default (every serializer field) would let clients sort on computed
      properties and crash with a FieldError.
    - Stable: appends `pk` as a tie-breaker so paginated results don't repeat
      or drop rows when many share the sorted value (e.g. same status).
    """

    def get_default_valid_fields(self, queryset, view, context=None):
        return []

    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view)
        if not ordering:
            return ordering
        if not any(f.lstrip("-") in ("pk", "id") for f in ordering):
            ordering = [*ordering, "pk"]
        return ordering
