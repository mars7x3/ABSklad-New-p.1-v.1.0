from rest_framework import generics, filters

from crm_general.filters import FilterByFields
from crm_general.permissions import IsStaff
from crm_general.utils import string_date_to_date, list_of_date_stings

from .models import StockGroupStat
from .serializers import StockGroupSerializer


class StockGroupAPIView(generics.ListAPIView):
    # permission_classes = (permissions.IsAuthenticated, IsStaff)
    queryset = StockGroupStat.objects.all()
    serializer_class = StockGroupSerializer
    filter_backends = (FilterByFields, filters.OrderingFilter)
    filter_by_fields = {
        "type": {"by": "stat_type", "type": "string", "required": False,
                 "addition_schema_params": {"enum": [stat_type for stat_type, _ in StockGroupStat.StatType.choices]},
                 "default": StockGroupStat.StatType.month,
                 "description": "By default month"},
        "start_date": {"by": "date__gte", "type": "date", "pipline": string_date_to_date,
                       "addition_filters": {"stat_type": StockGroupStat.StatType.day},
                       "ignore_on_filters": ("months", "weeks")},
        "end_date": {"by": "date__lte", "type": "date", "pipline": string_date_to_date,
                     "addition_filters": {"stat_type": StockGroupStat.StatType.day},
                     "ignore_on_filters": ("months", "weeks")},
        "months": {"by": "date__in", "type": "date", "pipline": list_of_date_stings("%Y-%m"),
                   "addition_filters": {"stat_type": StockGroupStat.StatType.month},
                   "description": "when using this parameter the type value will be counted as month."},
        "weeks": {"by": "date__in", "type": "date", "pipline": list_of_date_stings(),
                  "addition_filters": {"stat_type": StockGroupStat.StatType.week},
                  "ignore_on_filters": ("months",),
                  "description": "when using this parameter the type value will be counted as week."},
    }
    ordering_fields = (
        "stock__title", "date", "incoming_bank_amount", "incoming_cash_amount",
        "sales_products_count", "sales_amount", "sales_count", "sales_users_count", "sales_avg_check",
        "dealers_incoming_funds", "dealers_products_count", "dealers_amount", "dealers_avg_check",
        "products_amount", "products_user_count", "products_avg_check"
    )
