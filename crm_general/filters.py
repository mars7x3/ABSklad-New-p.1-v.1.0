from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework.filters import BaseFilterBackend

from crm_general.utils import string_date_to_datetime


class BaseFilter(BaseFilterBackend):
    def get_filters(self, request) -> dict:
        raise {}

    def filter_queryset(self, request, queryset, view):
        filters = self.get_filters(request)
        if filters:
            return queryset.filter(**filters)
        return queryset

    def get_schema_operation_parameters(self, view):
        return []


class ActiveFilterMixin:
    active_field: str = "is_active"
    active_param: str = "active"
    active_description = _("Filter active or deactivated status")

    def get_filters(self, request):
        filters = super().get_filters(request)
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
                'name': self.active_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.active_description),
                'schema': {
                    'type': 'boolean'
                }
            }
        ] + super().get_schema_operation_parameters(view)


class DateRangeFilterMixin:
    start_date_field: str = "created_at__date"
    start_date_param: str = "date_start"
    start_description = _("Filter objects that were made after the specified date")

    end_date_field: str = "created_at__date"
    end_date_param: str = "date_end"
    end_description = _("Filter objects that were made before the specified date")

    def get_filters(self, request):
        filters = super().get_filters(request)
        start = request.query_params.get(self.start_date_param)
        if start:
            filters[self.start_date_field + '__gte'] = string_date_to_datetime(start)

        end = request.query_params.get(self.end_date_param)
        if end:
            filters[self.start_date_field + '__lte'] = string_date_to_datetime(end)
        return filters

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': self.start_date_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.start_description),
                'schema': {
                    'type': 'date'
                }
            },
            {
                'name': self.end_date_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.end_description),
                'schema': {
                    'type': 'date'
                }
            }
        ] + super().get_schema_operation_parameters(view)


class ActiveFilter(ActiveFilterMixin, BaseFilter):
    pass
