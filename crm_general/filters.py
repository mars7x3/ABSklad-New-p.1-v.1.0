from django.utils.encoding import force_str
from rest_framework.filters import BaseFilterBackend
from rest_framework.validators import ValidationError


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

            ignore_on_filters = params.get('ignore_on_filters')
            found_ignore_filters = False
            for filter_source in ignore_on_filters or []:
                if request.query_params.get(filter_source):
                    found_ignore_filters = True
                    break

            if found_ignore_filters:
                continue

            value = request.query_params.get(source)
            if value:
                pipline = params.get("pipline")

                if pipline:
                    assert callable(pipline)
                    value = pipline(value)

                if value is None:
                    continue

                filters[params["by"]] = value

                addition_filters = params.get("addition_filters")
                if isinstance(addition_filters, dict) and addition_filters:
                    filters |= addition_filters
            else:
                default = params.get("default")

                if default:
                    filters[params["by"]] = default

        if filters:
            try:
                return queryset.filter(**filters)
            except (ValueError, TypeError) as e:
                raise ValidationError({"detail": "wrong params!"})
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
