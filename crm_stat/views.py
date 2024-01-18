from django.db.models import F, Sum, Value, Count, Case, When, DecimalField
from django.db.models.functions import JSONObject, Round
from rest_framework import views, generics, filters, permissions, exceptions, response

from crm_general.filters import FilterByFields
from crm_general.permissions import IsStaff
from crm_general.utils import string_date_to_date, list_of_date_stings, string_datetime_datetime
from one_c.models import MoneyDoc
from order.models import MyOrder

from .models import StockGroupStat, PurchaseStat, UserTransactionsStat
from .serializers import StockGroupSerializer, TransactionSerializer, OrderSerializer
from .utils import divide_into_weeks, sum_and_collect_by_map, date_filters


class StockGroupByWeekAPIView(views.APIView):
    permission_classes = (permissions.IsAuthenticated, IsStaff)
    summing_fields = dict(
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

    def get(self, request):
        start = request.query_params.get("start_date")
        end = request.query_params.get("end_date")
        if not start and not end:
            raise exceptions.ValidationError({"detail": "start_date and end_date is required params!"})

        start_date = string_datetime_datetime(start, datetime_format="%Y-%m-%d")
        end_date = string_datetime_datetime(end, datetime_format="%Y-%m-%d")

        collected_dates = []
        for start, end in divide_into_weeks(start_date, end_date):
            query = (
                StockGroupStat.objects.filter(
                    stat_type=StockGroupStat.StatType.day,
                    date__gte=start, date__lte=end
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
            )

            for data in sum_and_collect_by_map(query, self.summing_fields):
                data.pop("stock_stat_id", None)

                if all(value is None for value in data.values()):
                    continue

                data["date"] = start.date()
                collected_dates.append(data)
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


class DealerFundsView(views.APIView):
    permission_classes = (permissions.IsAuthenticated, IsStaff)

    def get(self, request, date):
        filter_type = request.query_params.get("type", "day")
        format_date = "%Y-%m-%d" if filter_type != "month" else "%Y-%m"
        date = string_datetime_datetime(date.strip(), datetime_format=format_date)
        query = date_filters(filter_type, date)
        stock_id = request.query_params.get("stock_id")
        if stock_id:
            query["stock_stat__stock_id"] = stock_id

        data = []
        for item in (
            UserTransactionsStat.objects.filter(**query)
            .values("user_stat_id")
            .annotate(
                user=JSONObject(
                    id=F("user_stat__user_id"),
                    name=F("user_stat__name")
                ),
                incoming_bank_amount=Sum("bank_income"),
                incoming_cash_amount=Sum("cash_income"),
                date=Value(str(date.date()))
            )
        ):
            item.pop("user_stat_id", None)
            data.append(item)
        return response.Response(data)


class DealerSalesView(views.APIView):
    permission_classes = (permissions.IsAuthenticated, IsStaff)

    def get(self, request, date):
        filter_type = request.query_params.get("type", "day")
        format_date = "%Y-%m-%d" if filter_type != "month" else "%Y-%m"
        date = string_datetime_datetime(date.strip(), datetime_format=format_date)
        query = date_filters(filter_type, date)

        stock_id = request.query_params.get("stock_id")
        if stock_id:
            query["stock_stat__stock_id"] = stock_id

        data = []
        for item in (
            PurchaseStat.objects.filter(**query)
            .values("user_stat_id")
            .annotate(
                user=JSONObject(
                    id=F("user_stat__user_id"),
                    name=F("user_stat__name")
                ),
                sales_products_count=Count("product_stat_id", distinct=True),
                sales_amount=Sum("spent_amount"),
                sales_count=Sum("purchases_count"),
                date=Value(str(date.date()))
            )
            .annotate(
                sales_avg_check=Case(
                    When(
                        sales_amount__gt=0,
                        then=F("sales_amount") / F("sales_count")
                    ),
                    default=Value(0.0),
                    output_field=DecimalField()
                )
            )
        ):
            item.pop("user_stat_id", None)
            data.append(item)
        return response.Response(data)


class DealerProductView(views.APIView):
    permission_classes = (permissions.IsAuthenticated, IsStaff)

    def get(self, request, date):
        filter_type = request.query_params.get("type", "day")
        format_date = "%Y-%m-%d" if filter_type != "month" else "%Y-%m"
        date = string_datetime_datetime(date.strip(), datetime_format=format_date)
        query = date_filters(filter_type, date)

        stock_id = request.query_params.get("stock_id")
        if stock_id:
            query["stock_stat__stock_id"] = stock_id

        data = []
        for item in (
            PurchaseStat.objects.filter(**query)
            .values("user_stat__user_id")
            .annotate(
                user=JSONObject(
                    id=F("user_stat__user_id"),
                    name=F("user_stat__name")
                ),
                products_amount=Sum("spent_amount"),
                sales_count=Sum("purchases_count"),
                date=Value(str(date.date()))
            )
            .annotate(
                sales_avg_check=Case(
                    When(
                        products_amount__gt=0, sales_count__gt=0,
                        then=F("products_amount") / F("sales_count")
                    ),
                    default=Value(0.0),
                    output_field=DecimalField()
                )
            )
        ):
            item.pop("user_stat__user_id", None)
            item.pop("sales_count")
            data.append(item)
        return response.Response(data)


class DealerView(views.APIView):
    permission_classes = (permissions.IsAuthenticated, IsStaff)

    def get(self, request, user_id, date):
        filter_type = request.query_params.get("type", "day")
        format_date = "%Y-%m-%d" if filter_type != "month" else "%Y-%m"
        date = string_datetime_datetime(date.strip(), datetime_format=format_date)
        query = date_filters(filter_type, date)

        stock_id = request.query_params.get("stock_id")
        if stock_id:
            query["stock_stat__stock_id"] = stock_id

        queryset = (
            PurchaseStat.objects.filter(user_stat__user_id=user_id, **query)
            .values("stock_stat__stock_id")
            .annotate(
                stock=JSONObject(
                    id=F("stock_stat__stock_id"),
                    title=F("stock_stat__title")
                ),
                dealers_amount=Sum("spent_amount"),
            )
            .annotate(
                dealers_avg_check=Round(
                    Case(
                        When(
                            dealers_amount__gt=0,
                            then=F("dealers_amount") / Sum("purchases_count")
                        ),
                        default=Value(0.0),
                        output_field=DecimalField()
                    ),
                    precision=2
                )
            )
        )
        include_products_count = request.query_params.get("include_products", "")
        if include_products_count == "true":
            queryset = queryset.annotate(dealers_products_count=Count("product_stat_id", distinct=True))

        include_funds = request.query_params.get("include_funds", "")
        if include_funds == "true":
            queryset = (
                queryset
                .annotate_funds(stock_stat__stock_id=stock_id, user_stat__user_id=user_id)
                .annotate(
                    dealers_incoming_funds=F("incoming_bank_amount") + F("incoming_cash_amount"),
                )
            )

        data = []
        for item in queryset:
            item.pop("bank_amount", None)
            item.pop("cash_amount", None)
            item.pop("incoming_users_count", None)
            item.pop("incoming_bank_amount", None)
            item.pop("incoming_cash_amount", None)

            item.pop("stock_stat__stock_id", None)
            item["date"] = str(date.date())
            data.append(item)
        return response.Response(data)


class ProductSalesView(views.APIView):
    permission_classes = (permissions.IsAuthenticated, IsStaff)

    def get(self, request, date):
        filter_type = request.query_params.get("type", "day")
        format_date = "%Y-%m-%d" if filter_type != "month" else "%Y-%m"
        date = string_datetime_datetime(date.strip(), datetime_format=format_date)
        query = date_filters(filter_type, date)

        stock_id = request.query_params.get("stock_id")
        if stock_id:
            query["stock_stat__stock_id"] = stock_id

        data = []
        for item in (
            PurchaseStat.objects.filter(**query)
            .values("product_stat_id")
            .annotate(
                product=JSONObject(
                    id=F("product_stat__product_id"),
                    title=F("product_stat__title")
                ),
                sales_amount=Sum("spent_amount"),
                sales_count=Sum("purchases_count"),
                date=Value(str(date.date()))
            )
            .annotate(
                sales_avg_check=Case(
                    When(
                        sales_amount__gt=0,
                        then=F("sales_amount") / F("sales_count")
                    ),
                    default=Value(0.0),
                    output_field=DecimalField()
                )
            )
        ):
            item.pop("product_stat_id", None)
            data.append(item)
        return response.Response(data)


class ProductDealersView(views.APIView):
    permission_classes = (permissions.IsAuthenticated, IsStaff)

    def get(self, request, date):
        filter_type = request.query_params.get("type", "day")
        format_date = "%Y-%m-%d" if filter_type != "month" else "%Y-%m"
        date = string_datetime_datetime(date.strip(), datetime_format=format_date)
        query = date_filters(filter_type, date)

        stock_id = request.query_params.get("stock_id")
        if stock_id:
            query["stock_stat__stock_id"] = stock_id

        data = []
        for item in (
            PurchaseStat.objects.filter(**query)
            .values("product_stat_id")
            .annotate_funds(**query)
            .annotate(
                product=JSONObject(
                    id=F("product_stat__product_id"),
                    title=F("product_stat__title")
                ),
                dealers_incoming_funds=F("incoming_bank_amount") + F("incoming_cash_amount"),
                dealers_products_count=Count("product_stat_id", distinct=True),
                dealers_amount=Sum("spent_amount"),
                date=Value(str(date.date()))
            )
            .annotate(
                dealers_avg_check=Case(
                    When(dealers_amount__gt=0, then=F("dealers_amount") / Sum("purchases_count")),
                    default=Value(0.0),
                    output_field=DecimalField()
                )
            )
        ):
            item.pop("bank_amount", None)
            item.pop("cash_amount", None)
            item.pop("incoming_users_count", None)
            item.pop("incoming_bank_amount", None)
            item.pop("incoming_cash_amount", None)
            item.pop("product_stat_id", None)
            data.append(item)
        return response.Response(data)


class ProductView(views.APIView):
    permission_classes = (permissions.IsAuthenticated, IsStaff)

    def get(self, request, product_id, date):
        filter_type = request.query_params.get("type", "day")
        format_date = "%Y-%m-%d" if filter_type != "month" else "%Y-%m"
        date = string_datetime_datetime(date.strip(), datetime_format=format_date)
        query = date_filters(filter_type, date)

        stock_id = request.query_params.get("stock_id")
        if stock_id:
            query["stock_stat__stock_id"] = stock_id

        data = []
        queryset = (
            PurchaseStat.objects.filter(product_stat__product_id=product_id, **query)
            .values("product_stat_id")
            .annotate_funds(**query)
            .annotate(
                product=JSONObject(
                    id=F("product_stat__product_id"),
                    title=F("product_stat__title")
                ),
                products_amount=Sum("spent_amount"),
                date=Value(str(date.date()))
            )
            .annotate(
                products_avg_check=Case(
                    When(products_amount__gt=0, then=F("products_amount") / Sum("purchases_count")),
                    default=Value(0.0),
                    output_field=DecimalField()
                )
            )
        )

        include_users = request.query_params.get('include_users', "")
        if include_users == "true":
            queryset = queryset.annotate(products_user_count=Count("user_stat__user_id", distinct=True))

        for item in queryset:
            item.pop("bank_amount", None)
            item.pop("cash_amount", None)
            item.pop("incoming_users_count", None)
            item.pop("incoming_bank_amount", None)
            item.pop("incoming_cash_amount", None)
            item.pop("product_stat_id", None)
            data.append(item)
        return response.Response(data)


class TransactionView(views.APIView):
    permission_classes = (permissions.IsAuthenticated, IsStaff)

    def get(self, request, date):
        filter_type = request.query_params.get("type", "day")
        format_date = "%Y-%m-%d" if filter_type != "month" else "%Y-%m"
        date = string_datetime_datetime(date.strip(), datetime_format=format_date)
        query = date_filters(filter_type, date, "created_at__date")
        user_id = request.query_params.get("user_id")
        if user_id:
            query["user_id"] = user_id

        stock_id = request.query_params.get("stock_id")
        if stock_id:
            query["cash_box__stock_id"] = stock_id

        status = request.query_params.get("status")
        match status:
            case "cash":
                query["status"] = "Нал"
            case "bank":
                query["status"] = "Без нал"

        queryset = MoneyDoc.objects.filter(is_active=True, user__isnull=False, **query).order_by("-created_at")
        serializer = TransactionSerializer(instance=queryset, many=True, context={"request": request, "view": self})
        return response.Response(serializer.data)


class OrderView(views.APIView):
    permission_classes = (permissions.IsAuthenticated, IsStaff)

    def get(self, request, date):
        filter_type = request.query_params.get("type", "day")
        format_date = "%Y-%m-%d" if filter_type != "month" else "%Y-%m"
        date = string_datetime_datetime(date.strip(), datetime_format=format_date)
        query = date_filters(filter_type, date, "created_at__date")
        product_id = request.query_params.get("product_id")
        if product_id:
            query["order_products__ab_product_id"] = product_id

        user_id = request.query_params.get("user_id")
        if user_id:
            query["author__user_id"] = user_id

        stock_id = request.query_params.get("stock_id")
        if stock_id:
            query["stock_id"] = stock_id

        queryset = MyOrder.objects.filter(**query).order_by("-created_at", "id").distinct()
        serializer = OrderSerializer(instance=queryset, many=True, context={"request": request, "view": self})
        return response.Response(serializer.data)
