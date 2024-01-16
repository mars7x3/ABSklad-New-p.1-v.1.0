from django.db.models import F, Sum
from django.db.models.functions import JSONObject
from django.utils import timezone
from rest_framework import views, generics, filters, permissions, exceptions, response

from crm_general.filters import FilterByFields
from crm_general.permissions import IsStaff
from crm_general.utils import string_date_to_date, list_of_date_stings, string_datetime_datetime

from .models import StockGroupStat
from .serializers import StockGroupSerializer


class StockGroupByWeekAPIView(views.APIView):
    # permission_classes = (permissions.IsAuthenticated, IsStaff)

    def get(self, request):
        start = request.query_params.get("start_date")
        end = request.query_params.get("end_date")
        if not start and not end:
            raise exceptions.ValidationError({"detail": "start_date and end_date is required params!"})

        start = string_datetime_datetime(start, datetime_format="%Y-%m-%d")
        end = string_datetime_datetime(end, datetime_format="%Y-%m-%d")

        weeks_count = round(end.day / 7)

        delta = timezone.timedelta(days=7)
        end_date = start + delta

        sum_fields_map = dict(
            incoming_bank_sum="incoming_bank_amount",
            incoming_cash_sum="incoming_cash_amount",
            incoming_users_qty="incoming_users_count",
            sales_products_qty="sales_products_count",
            sales_sum="sales_amount",
            sales_qty="sales_count",
            sales_users_qty="sales_users_count",
            sales_avg_check_sum="sales_avg_check",
            dealers_incoming_funds_sum="dealers_incoming_funds",
            dealers_products_qty="dealers_products_count",
            dealers_avg_check_sum="dealers_avg_check",
            products_sum="products_amount",
            products_user_qty="products_user_count",
            products_avg_check_sum="products_avg_check"
        )

        collected_dates = []
        for week_num in range(1, weeks_count + 1):
            data = (
                StockGroupStat.objects.filter(
                    stat_type=StockGroupStat.StatType.day,
                    date__gte=start, date__lte=end_date
                )
                .values("stock_stat_id")
                .annotate(
                    stock=JSONObject(
                        id=F("stock_stat__stock_id"),
                        title=F("stock_stat__title"),
                        address=F("stock_stat__address"),
                        is_active=F("stock_stat__is_active")
                    )
                )
                .annotate(**{field: Sum(source) for field, source in sum_fields_map.items()})
            )

            for item in data:
                collected_data = {}

                item.pop("stock_stat_id", None)
                for field, value in item.items():
                    source = sum_fields_map.get(field)
                    if not source:
                        collected_data[field] = value
                        continue

                    collected_data[source] = value

                if all(value is None for value in data.values()):
                    continue

                collected_data["date"] = start.date()
                collected_dates.append(collected_data)

            start += delta
            end_date += delta

        return response.Response(collected_dates)


class StockGroupAPIView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated, IsStaff)
    queryset = StockGroupStat.objects.all()
    serializer_class = StockGroupSerializer
    filter_backends = (FilterByFields, filters.OrderingFilter)
    filter_by_fields = {
        "type": {"by": "stat_type", "type": "string", "required": False,
                 "addition_schema_params": {"enum": [stat_type for stat_type, _ in StockGroupStat.StatType.choices]},
                 "default": StockGroupStat.StatType.month,
                 "description": "By default month"},
        "start_date": {"by": "date__gte", "type": "date", "pipline": string_date_to_date,
                       "ignore_on_filters": ("months", "weeks")},
        "end_date": {"by": "date__lte", "type": "date", "pipline": string_date_to_date,
                     "ignore_on_filters": ("months", "weeks")},
        "months": {"by": "date__in", "type": "date", "pipline": list_of_date_stings("%Y-%m"),
                   "addition_filters": {"stat_type": StockGroupStat.StatType.month},
                   "description": "when using this parameter the type value will be counted as month."},
    }
    ordering_fields = (
        "date", "incoming_bank_amount", "incoming_cash_amount",
        "sales_products_count", "sales_amount", "sales_count", "sales_users_count", "sales_avg_check",
        "dealers_incoming_funds", "dealers_products_count", "dealers_amount", "dealers_avg_check",
        "products_amount", "products_user_count", "products_avg_check"
    )
