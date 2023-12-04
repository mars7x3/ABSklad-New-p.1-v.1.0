from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework.filters import BaseFilterBackend


class OrderFilter(BaseFilterBackend):
    active_param = "active"
    active_description = _("Filter orders by active")
    status_param = "status"
    status_description = _("Filter orders by status")
    user_param = "user_id"
    user_description = _("Filter orders by user")
    start_date_param = "start_date"
    start_description = _("Filter orders that were made after the specified date")
    end_date_param = "end_date"
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
            filters['created_at__date__gte'] = start

        end = request.query_params.get(self.end_date_param)
        if end:
            filters['created_at__date__lte'] = end
        active = request.query_params.get(self.active_param)
        match active:
            case "1":
                filters['is_active'] = True
            case "0":
                filters['is_active'] = False
        return filters

    def filter_queryset(self, request, queryset, view):
        filters = self.get_filters(request, view)
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
                    'type': 'number'
                }
            },
            {
                'name': self.status_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.start_description),
                'schema': {
                    'type': 'string'
                }
            },
            {
                'name': self.user_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.user_description),
                'schema': {
                    'type': 'string'
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
                'required': True,
                'in': 'query',
                'description': force_str(self.end_description),
                'schema': {
                    'type': 'date'
                }
            },
        ]
