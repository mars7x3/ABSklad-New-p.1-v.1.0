from django.utils.encoding import force_str
from rest_framework.filters import BaseFilterBackend


class FilterByFields(BaseFilterBackend):
    filter_by_fields = "filter_by_fields"

    def get_filter_by_fields(self, view):
        return getattr(view, self.filter_by_fields, {})

    def filter_queryset(self, request, queryset, view):
        filter_by_fields = self.get_filter_by_fields(view)
        assert isinstance(filter_by_fields, dict)

        filters = {}

        for source, params in filter_by_fields.items():
            assert isinstance(params, dict)

            value = request.query_params.get(source)
            if value:
                pipline = params.get("pipline")

                if pipline:
                    assert callable(pipline)
                    value = pipline(value)

                if value is None:
                    continue

                filters[params["by"]] = value

        if filters:
            return queryset.filter(**filters)
        return queryset

    def get_schema_operation_parameters(self, view):
        filter_by_fields = self.get_filter_by_fields(view)
        assert isinstance(filter_by_fields, dict)

        schema_parameters_list = [
            {
                "name": source,
                "required": params.get("required", False),
                "in": "query",
                "description": force_str(params.get("description", "")),
                "schema": {
                    "type": params["type"],
                    **params.get("addition_schema_params", {})
                }
            }
            for source, params in filter_by_fields.items()
        ]
        return schema_parameters_list
