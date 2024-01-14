from datetime import datetime
from enum import Enum

from django.db.models import F, Q, Sum, Count, DecimalField, Subquery, Value, Case, When, OuterRef
from django.db.models.functions import TruncMonth, TruncDate, TruncWeek, ExtractMonth, ExtractYear
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from rest_framework.filters import BaseFilterBackend
from rest_framework.validators import ValidationError

from crm_stat.models import UserTransactionsStat


class FilterByEnum(Enum):
    months = "months"
    weeks = "weeks"
    days = "days"


class GroupedByStockDateFilter(BaseFilterBackend):
    param = "type"
    description = _("Filter by types: months, weeks, days")
    start_param = "start"
    end_param = "end"
    months_param = "months"

    def _get_start_and_end(self, request) -> tuple[datetime, datetime]:
        start = request.query_params.get(self.start_param)
        end = request.query_params.get(self.end_param)

        if not start or not end:
            raise ValidationError({"detail": "start and end is required!"})

        return datetime.strptime(start, "%Y-%m-%d"), datetime.strptime(end, "%Y-%m-%d")

    def _get_months(self, request) -> list[datetime]:
        months = request.query_params.get(self.months_param)
        if not months:
            raise ValidationError({"detail": "months is required!"})

        try:
            return [datetime.strptime(month, "%Y-%m") for month in months.split(',') if month]
        except ValueError as e:
            raise ValidationError({"months": str(e)})

    def filter_queryset(self, request, queryset, view):
        filter_by = request.query_params.get(self.param)
        date_filters_args, date_filters_kwargs = [], {}
        tx_date_filters_args, tx_date_filters_kwargs = [], {}

        match filter_by:
            case FilterByEnum.days.value:
                start, end = self._get_start_and_end(request)
                date_filters_kwargs["date__gte"] = start
                date_filters_kwargs["date__lte"] = end
                date_trunc = TruncDate
                tx_date_filters_kwargs["date"] = OuterRef("date")
            case FilterByEnum.weeks.value:
                start, end = self._get_start_and_end(request)
                date_filters_kwargs["date__gte"] = start
                date_filters_kwargs["date__lte"] = end
                date_trunc = TruncWeek
                tx_date_filters_kwargs["date"] = OuterRef("date")

            case _:
                month_conditions = Q()
                for date in self._get_months(request):
                    month_conditions |= Q(date__year=date.year, date__month=date.month)

                tx_date_filters_kwargs["date__month"] = OuterRef("month")
                tx_date_filters_kwargs["date__year"] = OuterRef("year")
                date_filters_args.append(month_conditions)
                date_trunc = TruncMonth

        return (
            queryset.filter(*date_filters_args, **date_filters_kwargs)
            .values(
                stat_date=date_trunc("date"),
                stock_title=F("stock_stat__title"),
                stock_id=F("stock_stat_id"),
            )
            .annotate(
                month=ExtractMonth('date'),
                year=ExtractYear('date')
            )
            .annotate(
                bank_amount=Subquery(
                    UserTransactionsStat.objects.filter(
                        stock_stat_id=OuterRef("stock_stat_id")
                    )
                    .values("bank_income")
                    .annotate(stat_date=date_trunc("date"))
                    .filter(stat_date=OuterRef("stat_date"))
                    .annotate(bank_amount=Sum("bank_income"))
                    .values("bank_amount")[:1]
                ),
                cash_amount=Subquery(
                    UserTransactionsStat.objects.filter(
                        stock_stat_id=OuterRef("stock_stat_id")
                    )
                    .values("cash_income")
                    .values("bank_income")
                    .annotate(stat_date=date_trunc("date"))
                    .filter(stat_date=OuterRef("stat_date"))
                    .annotate(cash_amount=Sum("cash_income"))
                    .values("cash_amount")[:1]
                )
            )
            .annotate(
                incoming_bank_amount=Case(
                    When(bank_amount__isnull=True, then=Value(0.0)),
                    default=F("bank_amount"),
                    output_field=DecimalField()
                ),
                incoming_cash_amount=Case(
                    When(cash_amount__isnull=True, then=Value(0.0)),
                    default=F("cash_amount"),
                    output_field=DecimalField()
                )
            )
            # sales
            .annotate(
                sales_products_count=Count(
                    "product_stat__product_id",
                    distinct=True
                ),
                sales_amount=Sum(
                    "spent_amount",
                    default=Value(0.0)
                ),
                sales_count=Count("id"),
                sales_users_count=Count("user_stat__user_id", distinct=True)
            )
            .annotate(
                sales_avg_check=Case(
                    When(sales_amount__gt=0, sales_count__gt=0, then=F("sales_amount") / F("sales_count")),
                    default=Value(0.0),
                    output_field=DecimalField()
                ),
            )
            # dealers and products
            .annotate(
                dealers_incoming_funds=F("incoming_bank_amount") + F("incoming_cash_amount"),
                dealers_products_count=F("sales_products_count"),
                dealers_amount=F("sales_amount"),
                dealers_avg_check=F("sales_avg_check"),
                products_amount=F("sales_amount"),
                products_user_count=F("sales_users_count"),
                products_avg_check=F("sales_avg_check")
            )
        )

    def get_schema_operation_parameters(self, view):
        return [
            {
                "name": self.param,
                "required": True,
                "in": "query",
                "description": force_str(self.description),
                "schema": {
                    "type": "string",
                    "enum": [FilterByEnum.months.value, FilterByEnum.weeks.value, FilterByEnum.days.value],
                }
            },
            {
                "name": self.start_param,
                "required": False,
                "in": "query",
                "description": "",
                "schema": {
                    "type": "date",
                }
            },
            {
                "name": self.end_param,
                "required": False,
                "in": "query",
                "description": "",
                "schema": {
                    "type": "date",
                }
            },
            {
                "name": self.months_param,
                "required": False,
                "in": "query",
                "description": "",
                "schema": {
                    "type": "string",
                }
            }
        ]
