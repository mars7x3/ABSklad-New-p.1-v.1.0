from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from order.models import MyOrder
from crm_general.filters import ActiveFilterMixin, BaseFilter, DateRangeFilterMixin


class OrderFilter(ActiveFilterMixin, DateRangeFilterMixin, BaseFilter):
    city_param = "city"
    city_description = _("Filter orders by stock city")
    status_param = "status"
    status_description = _("Filter orders by status")
    user_param = "user_id"
    user_description = _("Filter orders by user")

    def get_filters(self, request):
        filters = super().get_filters(request)
        status = request.query_params.get(self.status_param)
        if status:
            filters['status'] = status

        user_id = request.query_params.get(self.user_param)
        if user_id:
            filters['author__user_id'] = user_id

        city = request.query_params.get(self.city_param)
        if city:
            filters["stock__city__slug"] = city
        return filters

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
                'name': self.user_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.user_description),
                'schema': {
                    'type': 'number'
                }
            }
        ] + super().get_schema_operation_parameters(view)


class BalancePlusFilter(ActiveFilterMixin, DateRangeFilterMixin, BaseFilter):
    active_field = "is_success"
    active_param = "success"
    active_description = _("Filter balances by success status")


class WallerFilter(ActiveFilterMixin, BaseFilter):
    active_field = "user__user__is_active"


class StockFilter(ActiveFilterMixin, BaseFilter):
    pass
