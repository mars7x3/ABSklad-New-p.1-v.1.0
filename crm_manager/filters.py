import coreschema
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework.filters import BaseFilterBackend

from crm_manager.utils import query_date_to_datetime
from order.models import MyOrder


class OrderFilter(BaseFilterBackend):
    city_param = "city"
    city_description = _("Filter orders by stock city")
    active_param = "active"
    active_description = _("Filter active or deactivated orders")
    status_param = "status"
    status_description = _("Filter orders by status")
    user_param = "user_id"
    user_description = _("Filter orders by user")
    start_date_param = "date_start"
    start_description = _("Filter orders that were made after the specified date")
    end_date_param = "date_end"
    end_description = _("Filter orders that were made before the specified date")

    def get_filters(self, request, view):
        filters = {}
        status = request.query_params.get(self.status_param)
        if status:
            filters['status'] = status

        user_id = request.query_params.get(self.user_param)
        if user_id:
            filters['author__user_id'] = user_id

        start = request.query_params.get(self.start_date_param)
        if start:
            filters['created_at__date__gte'] = query_date_to_datetime(start)

        end = request.query_params.get(self.end_date_param)
        if end:
            filters['created_at__date__lte'] = query_date_to_datetime(end)

        active = request.query_params.get(self.active_param, "")
        match active.lower():
            case "true":
                filters['is_active'] = True
            case "false":
                filters['is_active'] = False

        city = request.query_params.get(self.city_param)
        if city:
            filters["stock__city__slug"] = city
        return filters

    def filter_queryset(self, request, queryset, view):
        filters = self.get_filters(request, view)
        if filters:
            return queryset.filter(**filters)
        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': self.status_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.status_description),
                'schema': {
                    'type': 'string',
                    'enum': [field for field, _ in MyOrder.STATUS]
                }
            },
            {
                'name': self.city_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.city_description),
                'schema': {
                    'type': 'string'
                }
            },
            {
                'name': self.active_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.active_description),
                'schema': {
                    'type': 'boolean',
                }
            },
            {
                'name': self.user_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.user_description),
                'schema': {
                    'type': 'number'
                }
            },
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
            },
        ]


class BalancePlusFilter(BaseFilterBackend):
    start_date_param = "date_start"
    start_description = _("Filter balances that were made after the specified date")
    end_date_param = "date_end"
    end_description = _("Filter balances that were made before the specified date")
    success_param = "success"
    success_description = _("Filter balances by success status")

    def get_filters(self, request):
        filters = {}

        start = request.query_params.get(self.start_date_param)
        if start:
            filters['created_at__date__gte'] = query_date_to_datetime(start)

        end = request.query_params.get(self.end_date_param)
        if end:
            filters['created_at__date__lte'] = query_date_to_datetime(end)

        success = request.query_params.get(self.success_param)
        match success:
            case "true":
                filters['is_success'] = True
            case "false":
                filters["is_success"] = False
        return filters

    def filter_queryset(self, request, queryset, view):
        filters = self.get_filters(request)
        if filters:
            return queryset.filter(**filters)
        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': self.success_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.success_description),
                'schema': {
                    'type': 'boolean',
                }
            },
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
        ]


class WallerFilter(BaseFilterBackend):
    active_param = "active"
    active_description = _("Filter active or deactivated wallets...")

    def get_filters(self, request):
        filters = {}
        active = request.query_params.get(self.active_param, "")
        match active.lower():
            case "true":
                filters['user__user__is_active'] = True
            case "false":
                filters["user__user__is_active"] = False
        return filters

    def filter_queryset(self, request, queryset, view):
        filters = self.get_filters(request)
        if filters:
            return queryset.filter(**filters)
        return queryset

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
        ]
