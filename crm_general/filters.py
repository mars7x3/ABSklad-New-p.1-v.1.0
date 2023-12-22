from decimal import Decimal

from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework.filters import BaseFilterBackend

from crm_general.utils import string_date_to_datetime


class BaseFilter(BaseFilterBackend):
    def get_filters(self, request, view) -> dict:
        return {}

    def filter_queryset(self, request, queryset, view):
        filters = self.get_filters(request, view)
        if filters:
            return queryset.filter(**filters)
        return queryset

    def get_schema_operation_parameters(self, view):
        return []


class ActiveFilterMixin:
    active_field: str = "is_active"
    active_param: str = "active"
    active_description = _("Filter active or deactivated status")

    def get_filters(self, request, view):
        filters = super().get_filters(request, view)
        active = request.query_params.get(self.active_param, "")
        match active.lower():
            case "true":
                filters[self.active_field] = True
            case "false":
                filters[self.active_field] = False
        return filters

    def get_schema_operation_parameters(self, view):
        return [
            {
                "name": self.active_param,
                "required": False,
                "in": "query",
                "description": force_str(self.active_description),
                "schema": {
                    "type": "boolean"
                }
            }
        ] + super().get_schema_operation_parameters(view)


class DateRangeFilterMixin:
    start_date_attr = "start_date_field"
    end_date_attr = "end_date_field"

    start_date_param: str = "date_start"
    start_description = _("Filter objects that were made after the specified date")

    end_date_param: str = "date_end"
    end_description = _("Filter objects that were made before the specified date")
    default_date_field = "created_at__date"

    def get_filters(self, request, view):
        filters = super().get_filters(request, view)
        query_start = request.query_params.get(self.start_date_param)
        if query_start:
            start = getattr(view, self.start_date_attr, self.default_date_field)
            filters[start + "__gte"] = string_date_to_datetime(query_start)

        query_end = request.query_params.get(self.end_date_param)
        if query_end:
            end = getattr(view, self.end_date_attr, self.default_date_field)
            filters[end + "__lte"] = string_date_to_datetime(query_end)
        return filters

    def get_schema_operation_parameters(self, view):
        return [
            {
                "name": self.start_date_param,
                "required": False,
                "in": "query",
                "description": force_str(self.start_description),
                "schema": {
                    "type": "date"
                }
            },
            {
                "name": self.end_date_param,
                "required": False,
                "in": "query",
                "description": force_str(self.end_description),
                "schema": {
                    "type": "date"
                }
            }
        ] + super().get_schema_operation_parameters(view)


class ActiveFilter(ActiveFilterMixin, BaseFilter):
    pass


class DateRangeFilter(DateRangeFilterMixin, BaseFilter):
    pass


class FilterByFields(BaseFilterBackend):
    filter_by_fields = "filter_by_fields"

    def get_filter_by_fields(self, view):
        return getattr(view, self.filter_by_fields)

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


class ChoiceFilter(BaseFilterBackend):
    choice_attr = "choice_fields"

    def get_choice_fields(self, view, request) -> dict:
        choice_params = getattr(view, self.choice_attr)
        assert isinstance(choice_params, dict)

        filters = {}
        for source, params in choice_params.items():
            assert "db_field" in params
            assert "choices" in params

            query_param = request.query_params.get(source)
            if query_param and query_param in params["choices"]:
                filters[params["db_field"]] = query_param
        return filters

    def filter_queryset(self, request, queryset, view):
        filters = self.get_choice_fields(view, request)
        if filters:
            return queryset.filter(**filters)
        return queryset

    def get_schema_operation_parameters(self, view):
        choice_params = getattr(view, self.choice_attr)
        assert choice_params
        assert isinstance(choice_params, dict)

        schema_fields = []
        for source, params in choice_params.items():
            assert isinstance(params, dict)
            assert "db_field" in params
            if all(isinstance(choice, bool) for choice in params["choices"]):
                field_type = "boolean"
            elif all(isinstance(choice, int) for choice in params["choices"]):
                field_type = "integer"
            elif all(isinstance(choice, (int, float, Decimal)) for choice in params["choices"]):
                field_type = "number"
            else:
                field_type = "string"

            schema_fields.append(
                {
                    "name": field_type,
                    "required": False,
                    "in": "query",
                    "description": force_str(params.get("description", "")),
                    "schema": {
                        "type": field_type,
                        "enum": params["choices"]
                    },
                }
            )
        return schema_fields
