from datetime import datetime
from logging import getLogger

from django.db import models
from django.db.models.functions import TruncDate
from django.utils import timezone

from general_service.models import City, Stock
from absklad_commerce.celery import app
from one_c.models import MoneyDoc
from order.models import MyOrder, OrderProduct

from .models import CityStat, StockStat, UserStat, UserTransactionsStat, ProductStat, PurchaseStat
from .utils import Builder, stat_create_or_update

logger = getLogger('statistics')
city_builder = Builder(
    model=CityStat,
    fields_map={
        "city_id": "id",
        "title": "title",
        "is_active": "is_active"
    }
)

stock_builder = Builder(
    model=StockStat,
    fields_map={
        "stock_id": "id",
        "title": "title",
        "address": "address",
        "city_stat_id": "city_id",
        "is_active": "is_active"
    }
)

user_builder = Builder(
    model=UserStat,
    fields_map={
        "user_id": "user_id",
        "city_stat_id": "city_id",
        "email": "email",
        "name": "name"
    }
)

product_builder = Builder(
    model=ProductStat,
    fields_map={
        "product_id": "product_id",
        "title": "title",
        "vendor_code": "vendor_code",
        "category_id": "category_id",
        "collection_id": "collection_id"
    }
)

user_transaction_builder = Builder(
    model=UserTransactionsStat,
    fields_map={
        "user_stat_id": "user_id",
        "stock_stat_id": "stock_id",
        "bank_income": "bank_income",
        "cash_income": "cash_income",
        "date": "date"
    }
)

purchase_builder = Builder(
    model=PurchaseStat,
    fields_map={
        "user_stat_id": "user_id",
        "product_stat_id": "product_id",
        "stock_stat_id": "stock_id",
        "spent_amount": "spent_amount",
        "count": "count",
        "purchases_count": "purchases_count",
        "avg_check": "avg_check",
        "date": "date"
    }
)


@app.task
def save_city_stats():
    processed_objs = stat_create_or_update(
        queryset=City.objects.filter(is_active=True),
        builder=city_builder,
        match_field="city_id",
        match_field_y="id",
        update_ignore_fields=["city_id"]
    )
    logger.info(f"Successfully collected cities")
    return set(map(lambda obj: obj.id, processed_objs))


@app.task
def save_stock_stats(city_relations):
    processed_objs = stat_create_or_update(
        queryset=Stock.objects.all(),
        builder=stock_builder,
        match_field="stock_id",
        match_field_y="id",
        update_ignore_fields=["stock_id"],
        relations={"city_stat_id": city_relations}
    )
    logger.info(f"Successfully collected stocks")
    return set(map(lambda obj: obj.id, processed_objs))


@app.task
def save_user_stats(ts: int, city_relations: dict):
    date_from_ts = datetime.fromtimestamp(ts).date()
    orders_query = (
        MyOrder.objects.filter(
            created_at__date=date_from_ts,
            status__in=("success", "sent"),
            is_active=True,
            author__village__city_id__in=list(city_relations.keys())
        )
    )

    def on_save_users(queryset):
        return (
            queryset
            .values(user_id=models.F("author__user_id"))
            .annotate(
                city_id=models.F("author__village__city_id"),
                email=models.F("author__user__email"),
                name=models.F("author__user__name")
            )
        )

    processed_objs = stat_create_or_update(
        queryset=orders_query,
        builder=user_builder,
        match_field="user_id",
        match_field_y="author__user_id",
        update_ignore_fields=["user_id"],
        relations={"city_stat_id": city_relations},
        on_create=on_save_users,
        on_update=on_save_users
    )
    logger.info(f"Successfully collected users for date {date_from_ts}")
    return set(map(lambda obj: obj.id, processed_objs))


@app.task
def save_product_stats(ts: int):
    date_from_ts = datetime.fromtimestamp(ts).date()
    order_products = OrderProduct.objects.filter(
        order__created_at__date=date_from_ts,
        order__status__in=("success", "sent"),
        order__is_active=True,
        ab_product__isnull=False,
        order__stock__isnull=False
    )

    def on_save_product(queryset):
        return (
            queryset
            .values(product_id=models.F("ab_product_id"))
            .annotate(
                title=models.F("ab_product__title"),
                vendor_code=models.F("ab_product__vendor_code"),
                category_id=models.F("ab_product__category_id"),
                collection_id=models.F("ab_product__collection_id")
            )
        )

    processed_objs = stat_create_or_update(
        queryset=order_products,
        builder=product_builder,
        match_field="product_id",
        match_field_y="ab_product_id",
        update_ignore_fields=["product_id"],
        on_create=on_save_product,
        on_update=on_save_product
    )
    logger.info(f"Successfully collected products for date {date_from_ts}")
    return set(map(lambda obj: obj.id, processed_objs))


def save_transaction_stats(ts: int, user_relations, stock_relations, city_relations):
    date_from_ts = datetime.fromtimestamp(ts).date()
    transactions = MoneyDoc.objects.filter(
        is_active=True,
        created_at__date=date_from_ts,
        user__in=list(user_relations.keys()),
        cash_box__stock__in=list(stock_relations.keys())
    )

    if not transactions.exists():
        logger.error(f"Not found transactions for date {date_from_ts}")
        return

    users = transactions.filter(user__dealer_profile__village__city_id__in=list(city_relations.keys()))
    saved_user_ids = UserStat.objects.values_list("user_id", flat=True)
    if saved_user_ids:
        users = users.exclude(user_id__in=saved_user_ids)

    if users.exists():
        new_users = user_builder.build_model_by_list(
            items=(
                users
                .values("user_id")
                .annotate(
                    city_id=models.F("user__dealer_profile__village__city_id"),
                    email=models.F("user__email"),
                    name=models.F("user__name")
                )
            ),
            match_field="user_id",
            relations={"city_stat_id": city_relations}
        )

        user_relations |= {
            getattr(user_stat, "user_id"): user_stat.id
            for user_stat in UserStat.objects.bulk_create(new_users)
        }

    new_transaction_stats = user_transaction_builder.build_model_by_list(
        items=(
            transactions
            .values("user_id")
            .annotate(
                stock_id=models.F("cash_box__stock_id"),
                date=TruncDate("created_at"),
                bank_income_value=models.Sum("amount", filter=models.Q(status="Без нал")),
                cash_income_value=models.Sum("amount", filter=models.Q(status="Нал")),
            )
            .annotate(
                bank_income=models.Case(
                    models.When(
                        bank_income_value__isnull=False,
                        then=models.F("bank_income_value")
                    ),
                    default=models.Value(0.0),
                    output_field=models.DecimalField()
                ),
                cash_income=models.Case(
                    models.When(
                        cash_income_value__isnull=False,
                        then=models.F("cash_income_value")
                    ),
                    default=models.Value(0.0),
                    output_field=models.DecimalField()
                )
            )
        ),
        match_field="user_id",
        relations={
            "user_stat_id": user_relations,
            "stock_stat_id": stock_relations
        }
    )
    UserTransactionsStat.objects.bulk_create(new_transaction_stats)
    logger.info(f"Successfully collected user transactions for date {date_from_ts}")


@app.task
def save_purchase_stats(ts: int, user_relations, product_relations, stock_relations):
    date_from_ts = datetime.fromtimestamp(ts).date()
    purchases = MyOrder.objects.filter(
        created_at__date=date_from_ts,
        status__in=("success", "sent"),
        is_active=True,
        stock__isnull=False,
        order_products__ab_product__isnull=False
    )
    if not purchases.exists():
        logger.error(f"Not found purchases for date {date_from_ts}")
        return

    purchases = (
        purchases
        .values(user_id=models.F("author__user_id"))
        .annotate(
            date=TruncDate("created_at"),
            product_id=models.F("order_products__ab_product_id"),
            stock_id=models.F("stock_id"),
            spent_amount=models.Sum("order_products__total_price"),
            count=models.Sum("order_products__count"),
            purchases_count=models.Count("order_products__id")
        )
        .annotate(
            cost_price=models.F("order_products__cost_price"),
            avg_check=models.ExpressionWrapper(
                models.F("spent_amount") / models.F("purchases_count"),
                output_field=models.DecimalField()
            )
        )
    )
    new_purchase_stats = purchase_builder.build_model_by_list(
        items=purchases,
        match_field=("user_id", "product_id", "stock_id"),
        relations={
            "user_stat_id": user_relations,
            "product_stat_id": product_relations,
            "stock_stat_id": stock_relations
        }
    )
    PurchaseStat.objects.bulk_create(new_purchase_stats)
    logger.info(f"Successfully collected products for date {date_from_ts}")


def collects_stats_for_date(time: datetime):
    ts = time.timestamp()
    date = time.date()

    processed_city_stat_ids = save_city_stats()
    city_relations = {
        city_id: city_stat_id
        for city_stat_id, city_id in (
            CityStat.objects.filter(id__in=processed_city_stat_ids).values_list("id", "city_id")
        )
    }
    if not city_relations:
        raise ValueError("Not found cities stats!")

    processed_stock_stat_ids = save_stock_stats(city_relations)
    processed_user_stat_ids = save_user_stats(ts, city_relations=city_relations)
    processed_product_stat_ids = save_product_stats(ts)

    stock_relations = {
        stock_id: stock_stat_id
        for stock_stat_id, stock_id in (
            StockStat.objects.filter(id__in=processed_stock_stat_ids).values_list("id", "stock_id")
        )
    }
    user_relations = {
        user_id: user_stat_id
        for user_stat_id, user_id in (
            UserStat.objects.filter(id__in=processed_user_stat_ids).values_list("id", "user_id")
        )
    }

    if not stock_relations or not user_relations:
        raise ValueError("Not fount stock or user stats!")

    UserTransactionsStat.objects.filter(date=date).delete()
    save_transaction_stats(ts, city_relations=city_relations, stock_relations=stock_relations,
                           user_relations=user_relations)

    product_relations = {
        product_id: product_stat_id
        for product_stat_id, product_id in (
            ProductStat.objects.filter(id__in=processed_product_stat_ids).values_list("id", "product_id")
        )
    }
    if not product_relations:
        raise ValueError("Not found product relations!")

    PurchaseStat.objects.filter(date=date).delete()
    save_purchase_stats(
        ts,
        user_relations=user_relations,
        product_relations=product_relations,
        stock_relations=stock_relations
    )


@app.task
def collect_today_stats():
    today = timezone.now()
    collects_stats_for_date(today)


def collect_for_all_dates():
    dates = set(order["date"] for order in MyOrder.objects.filter(is_active=True).values(date=TruncDate("created_at")))
    for date in dates:
        collects_stats_for_date(datetime(month=date.month, year=date.year, day=date.day))
