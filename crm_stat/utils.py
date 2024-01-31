import math
from datetime import datetime
from logging import getLogger
from typing import Iterable, Self

from django.db.models import F, Sum, Count, Case, When, Subquery, Value, DecimalField, QuerySet, Q
from django.utils import timezone
from django.utils.functional import cached_property
from rest_framework.request import Request

from crm_general.utils import string_datetime_datetime
from one_c.models import MoneyDoc
from order.models import MyOrder, OrderProduct

from .models import UserTransactionsStat, PurchaseStat, StockGroupStat


logger = getLogger('statistics')


def create_empty_group_stat(date, stat_type, stock) -> QuerySet:
    return StockGroupStat.objects.create(
        date=date,
        stat_type=stat_type,
        stock=stock,
    )


def divide_into_weeks(start: datetime, end: datetime) -> Iterable[tuple[datetime, datetime]]:
    assert end > start

    weeks_count = math.ceil(end.day / 7)
    temp_end = start + timezone.timedelta(days=6)

    for week_num in range(1, weeks_count + 1):
        if temp_end > end:
            temp_end = end

        yield start, temp_end

        start += timezone.timedelta(days=7)
        temp_end += timezone.timedelta(days=7)

        if temp_end == start:
            break


def sum_and_collect_by_map(queryset, fields_map) -> Iterable[dict]:
    data = queryset.annotate(**{field: Sum(source) for field, source in fields_map.items()})

    for item in data:
        collected_data = {}

        for field, value in item.items():
            source = fields_map.get(field)
            if not source:
                collected_data[field] = value
                continue

            collected_data[source] = value

        yield collected_data


class DateFilter:
    def __init__(self, filter_type: str, date: datetime, date_field: str = None, end: datetime = None):
        self.filter_type = filter_type
        self.start = date
        self.date_field = date_field or "date"
        self.end = end if end else self.start + timezone.timedelta(days=7)

    @cached_property
    def queries(self):
        query = {}
        match self.filter_type:
            case "month":
                query[self.date_field + "__month"] = self.start.month
                query[self.date_field + "__year"] = self.start.year
            case "week":
                query[self.date_field + "__gte"] = self.start
                query[self.date_field + "__lte"] = self.end
            case _:
                query[self.date_field] = self.start
        return query

    @classmethod
    def for_request(cls, request: Request, date: str, date_field: str = None) -> Self:
        filter_type = request.query_params.get("type", "day")
        datetime_format = "%Y-%m-%d" if filter_type != "month" else "%Y-%m"
        date = string_datetime_datetime(date.strip(), datetime_format=datetime_format)
        end = request.query_params.get("end")
        if end:
            end = string_datetime_datetime(end.strip(), datetime_format=datetime_format)

        return cls(
            filter_type=filter_type,
            date=date,
            date_field=date_field,
            end=end
        )

    @property
    def end_date_for_week(self):
        if self.filter_type == "week":
            return self.end.date()


def update_purchase_stat_group(group: StockGroupStat, queryset) -> None:
    orders_query = dict(
        stock=group.stock,
        is_active=True,
        status__in=("success", "sent"),
    )
    if group.stat_type == StockGroupStat.StatType.month:
        orders_query["released_at__month"] = group.date.month
        orders_query["released_at__year"] = group.date.year
    else:
        orders_query["released_at__date"] = group.date

    update_data = (
        queryset
        .values("stock_id")
        .annotate(
            sales_products_count=Count("product_id", distinct=True),
            sales_amount=Sum("spent_amount", default=Value(0.0)),
            sales_count=Subquery(
                MyOrder.objects.filter(**orders_query)
                .annotate(count=Count("id", distinct=True))
                .values('count')[:1]
            ),
        )
        .annotate(
            sales_users_count=Count("user_id", distinct=True, filter=Q(spent_amount__gt=0, count__gt=0)),
            sales_avg_check=Case(
                When(
                    sales_amount__gt=0,
                    sales_count__gt=0,
                    then=F("sales_amount") / F("sales_count")
                ),
                default=Value(0.0),
                output_field=DecimalField()
            )
        )[0]
    )
    # sales
    group.sales_products_count = update_data["sales_products_count"] or 0
    group.sales_amount = update_data["sales_amount"] or 0
    group.sales_count = update_data["sales_count"] or 0
    group.sales_users_count = update_data["sales_users_count"] or 0
    group.sales_avg_check = update_data["sales_avg_check"] or 0
    # dealers
    group.dealers_amount = update_data["sales_amount"] or 0
    group.dealers_products_count = update_data["sales_products_count"] or 0
    group.dealers_avg_check = update_data["sales_avg_check"] or 0
    # products
    group.products_amount = update_data["sales_amount"] or 0
    group.products_user_count = update_data["sales_users_count"] or 0
    group.products_avg_check = update_data["sales_avg_check"] or 0
    group.save()


def update_tx_stat_group(group: StockGroupStat, queryset):
    update_data = (
        queryset
        .aggregate(
            incoming_bank_amount=Sum("bank_income"),
            incoming_cash_amount=Sum("cash_income"),
            incoming_users_count=Count("user_id", filter=Q(bank_income__gt=0) | Q(cash_income__gt=0),
                                       distinct=True),
            dealers_incoming_funds=Sum("bank_income") + Sum("cash_income")
        )
    )
    group.incoming_bank_amount = update_data["incoming_bank_amount"] or 0
    group.incoming_cash_amount = update_data["incoming_cash_amount"] or 0
    group.incoming_users_count = update_data["incoming_users_count"]
    group.dealers_incoming_funds = update_data["dealers_incoming_funds"] or 0
    group.save()


def update_transaction_stat(tx: MoneyDoc) -> None:
    if not tx.cash_box:
        logger.error("MoneyDoc ID: %s must have cash_box for founding stock!")
        return

    if tx.is_checked:
        logger.debug("MoneyDoc ID: %s was used in stats!")
        return

    tx_stat = UserTransactionsStat.objects.filter(
        date=tx.created_at.date(),
        user=tx.user,
        stock=tx.cash_box.stock
    ).first()

    created = True
    if not tx_stat:
        tx_stat = UserTransactionsStat(
            date=tx.created_at.date(),
            user=tx.user,
            stock=tx.cash_box.stock,
            bank_income=0,
            cash_income=0
        )
        created = False

    update_field = "cash_income" if tx.status != "Без нал" else "bank_income"
    if tx.is_active:
        setattr(tx_stat, update_field, tx.amount + getattr(tx_stat, update_field))
    else:
        saved_amount = getattr(tx_stat, update_field)

        if saved_amount < tx.amount:
            if created:
                tx_stat.delete()
            return

        setattr(tx_stat, update_field, saved_amount - tx.amount)

    tx_stat.save()


def update_purchase_stat(order_product: OrderProduct) -> None:
    if order_product.is_checked:
        logger.debug("OrderProduct with ID %s was checked!" % order_product.id)
        return

    if not order_product.ab_product:
        logger.error("OrderProduct.ab_product must have!")
        return

    order = order_product.order
    purchase_stat = PurchaseStat.objects.filter(
        date=order.created_at.date(),
        user=order.author.user,
        stock=order.stock,
        product=order_product.ab_product
    ).first()

    created = True
    if not purchase_stat:
        purchase_stat = PurchaseStat(
            date=order.created_at.date(),
            user=order.author.user,
            stock=order.stock,
            product=order_product.ab_product,
            count=0,
            spent_amount=0,
            purchases_count=0,
            avg_check=0
        )
        created = False

    if order.is_active:
        purchase_stat.count += order_product.count
        purchase_stat.spent_amount += order_product.total_price
        purchase_stat.purchases_count += 1
        purchase_stat.avg_check = purchase_stat.spent_amount / purchase_stat.purchases_count
    else:
        if order_product.count > purchase_stat.count:
            purchase_stat.count = 0
        else:
            purchase_stat.count -= order_product.count

        if order_product.total_price > purchase_stat.spent_amount:
            purchase_stat.spent_amount = 0
        else:
            purchase_stat.spent_amount -= order_product.total_price

        if purchase_stat.purchases_count > 0:
            purchase_stat.purchases_count -= 1
        else:
            purchase_stat.purchases_count = 0

        if purchase_stat.spent_amount > 0 and purchase_stat.purchases_count > 0:
            purchase_stat.avg_check = purchase_stat.spent_amount / purchase_stat.purchases_count
        else:
            purchase_stat.avg_check = 0

        values = (purchase_stat.count, purchase_stat.spent_amount)
        if all(value == 0 for value in values):
            if created:
                purchase_stat.delete()
            return

    purchase_stat.save()


def update_stat_group_by_order(order: MyOrder) -> None:
    new_purchase_stats = []

    for product in order.order_products.all():
        update_purchase_stat(product)

    if new_purchase_stats:
        PurchaseStat.objects.bulk_create(new_purchase_stats)


def collect_stats_for_all() -> None:
    orders = MyOrder.objects.filter(
        status__in=("send", "success"),
        is_active=True,
        stock__isnull=False,
        order_products__isnull=False
    ).distinct()

    for order in orders:
        update_stat_group_by_order(order)

        order.order_products.update(is_checked=True)

    txs = MoneyDoc.objects.filter(user__isnull=False, cash_box__isnull=False, is_active=True).distinct()
    for tx in txs:
        update_transaction_stat(tx)

    txs.update(is_checked=True)
