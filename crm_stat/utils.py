from datetime import datetime
from logging import getLogger
from typing import Iterable

from django.db.models import F, Sum, Count, Case, When, Subquery, Value, DecimalField, QuerySet
from django.utils import timezone

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


def divide_into_weeks(start, end) -> Iterable[tuple[datetime, datetime]]:
    weeks_count = round(end.day / 7)
    delta = timezone.timedelta(days=7)
    end_date = start + delta

    for week_num in range(1, weeks_count + 1):
        yield start, end_date
        start += delta
        end_date += delta


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


def date_filters(filter_type: str, date: datetime, date_field: str = "date") -> None:
    query = {}
    match filter_type:
        case "month":
            query[date_field + "__month"] = date.month
            query[date_field + "__year"] = date.year
        case "week":
            query[date_field + "__gte"] = date
            query[date_field + "__lte"] = date + timezone.timedelta(days=7)
        case _:
            query[date_field] = date
    return query


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
                .annotate(count=Count("id", distinct=True))[:1]
            ),
            sales_users_count=Count("user_id", distinct=True),
        )
        .annotate(
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
    group.sales_products_count = update_data["sales_products_count"]
    group.sales_amount = update_data["sales_amount"]
    group.sales_count = update_data["sales_count"]
    group.sales_users_count = update_data["sales_users_count"]
    group.sales_avg_check = update_data["sales_avg_check"]
    # dealers
    group.dealers_amount = update_data["sales_amount"]
    group.dealers_products_count = update_data["sales_products_count"]
    group.dealers_avg_check = update_data["sales_avg_check"]
    # products
    group.products_amount = update_data["sales_amount"]
    group.products_user_count = update_data["sales_users_count"]
    group.products_avg_check = update_data["sales_avg_check"]
    group.save()


def update_tx_stat_group(group: StockGroupStat, queryset):
    update_data = (
        queryset
        .aggregate(
            incoming_bank_amount=Sum("bank_income"),
            incoming_cash_amount=Sum("cash_income"),
            incoming_users_count=Count("user_id"),
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

    if not tx_stat:
        tx_stat = UserTransactionsStat(
            date=tx.created_at.date(),
            user=tx.user,
            stock=tx.cash_box.stock,
            bank_income=0,
            cash_income=0
        )

    update_field = "cash_income" if tx.status == "Без нал" else "bank_income"
    if tx.is_active:
        setattr(tx_stat, update_field, tx.amount + getattr(tx_stat, update_field))
    else:
        saved_amount = getattr(tx_stat, update_field)
        if saved_amount < tx.amount:
            setattr(tx_stat, update_field, 0)
        else:
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

    if not purchase_stat:
        purchase_stat = PurchaseStat(
            date=order.created_at.date(),
            user=order.author.user,
            stock=order.stock,
            product=order_product.ab_product,
            count=0,
            spent_amount=0,
            purchases_count=1,
            avg_check=0
        )

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

    purchase_stat.save()


def update_stat_group_by_order(order: MyOrder) -> None:
    new_purchase_stats = []
    saved_purchase_stats = PurchaseStat.objects.filter(
        date=order.released_at.date(),
        user=order.author.user,
        stock=order.stock
    ).values_list("product_id", flat=True)

    for product in order.order_products.all():
        if product.ab_product.id in saved_purchase_stats:
            new_purchase_stats.append(
                PurchaseStat(
                    date=order.released_at.date(),
                    user=order.author.user,
                    product=product.ab_product,
                    stock=order.stock,
                    spent_amount=product.total_price,
                    count=product.count,
                    avg_check=product.total_price
                )
            )
            continue
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

    txs = MoneyDoc.objects.filter(user__isnull=False, cash_box__isnull=False, is_active=True).distinct()
    for tx in txs:
        update_transaction_stat(tx)
