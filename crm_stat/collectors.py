from datetime import datetime
from logging import getLogger

from django.db import models
from django.db.models import functions

from account.models import MyUser
from general_service.models import City, Stock
from one_c.models import MoneyDoc
from order.models import MyOrder, OrderProduct

from .models import UserTransactionsStat, PurchaseStat, UserStat, ProductStat, StockStat, CityStat, StockGroupStat
from .utils import stat_create_or_update, Builder, get_stock_grouped_stats

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

stock_group_builder = Builder(
    model=StockGroupStat,
    fields_map={
        "stat_type": "stat_type",
        "date": "stat_date",
        "stock_stat_id": "stock_stat_id",
        "incoming_bank_amount": "incoming_bank_amount",
        "incoming_cash_amount": "incoming_cash_amount",
        "incoming_users_count": "incoming_users_count",
        "sales_products_count": "sales_products_count",
        "sales_amount": "sales_amount",
        "sales_count": "sales_count",
        "sales_users_count": "sales_users_count",
        "sales_avg_check": "sales_avg_check",
        "dealers_incoming_funds": "dealers_incoming_funds",
        "dealers_products_count": "dealers_products_count",
        "dealers_amount": "dealers_amount",
        "dealers_avg_check": "dealers_avg_check",
        "products_amount": "products_amount",
        "products_user_count": "products_user_count",
        "products_avg_check": "products_avg_check"
    }
)


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


def save_user_stats(date, city_relations: dict):
    users_query = (
        MyUser.objects
        .filter(status="dealer", dealer_profile__village__isnull=False, dealer_profile__isnull=False)
        .values(user_id=models.F("id"))
        .annotate(
            city_id=models.F("dealer_profile__village__city_id"),
            email=models.F("email"),
            name=models.F("name")
        )
    )

    processed_objs = stat_create_or_update(
        queryset=users_query,
        builder=user_builder,
        match_field="user_id",
        match_field_y="user_id",
        update_ignore_fields=["user_id"],
        relations={"city_stat_id": city_relations}
    )
    logger.info(f"Successfully collected users for date {date}")
    return set(map(lambda obj: obj.id, processed_objs))


def save_product_stats(date):
    order_products = OrderProduct.objects.filter(
        order__created_at__date=date,
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
    logger.info(f"Successfully collected products for date {date}")
    return set(map(lambda obj: obj.id, processed_objs))


def save_transaction_stats(date, user_relations, stock_relations):
    transactions = MoneyDoc.objects.filter(
        is_active=True,
        created_at__date=date,
        user__isnull=False,
        cash_box__stock__in=stock_relations.keys()
    )

    if not transactions.exists():
        logger.error(f"Not found transactions for date {date}")
        return

    new_transaction_stats = user_transaction_builder.build_model_by_list(
        items=(
            transactions
            .values("user_id", "cash_box__stock_id")
            .annotate(
                stock_id=models.F("cash_box__stock_id"),
                date=functions.TruncDate("created_at"),
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
    logger.info(f"Successfully collected user transactions for date {date}")


def save_purchase_stats(date, user_relations, product_relations, stock_relations):
    purchases = MyOrder.objects.filter(
        created_at__date=date,
        status__in=("success", "sent"),
        is_active=True,
        stock__isnull=False,
        order_products__ab_product__isnull=False
    )
    if not purchases.exists():
        logger.error(f"Not found purchases for date {date}")
        return

    purchases = (
        purchases
        .values(user_id=models.F("author__user_id"))
        .annotate(
            date=functions.TruncDate("created_at"),
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
    logger.info(f"Successfully collected products for date {date}")


def collects_stats_for_date(time: datetime):
    date = time.date()

    processed_city_stat_ids = save_city_stats()
    city_stat_query = CityStat.objects.all()
    if processed_city_stat_ids:
        city_stat_query = city_stat_query.filter(id__in=processed_city_stat_ids)

    city_relations = {
        city_id: city_stat_id
        for city_stat_id, city_id in city_stat_query.values_list("id", "city_id")
    }
    if not city_relations:
        logger.error("Not found cities stats!")
        return

    stock_stat_query = StockStat.objects.all()
    user_stat_query = UserStat.objects.all()

    processed_stock_stat_ids = save_stock_stats(city_relations)
    if processed_stock_stat_ids:
        stock_stat_query = stock_stat_query.filter(id__in=processed_stock_stat_ids)

    processed_user_stat_ids = save_user_stats(date, city_relations=city_relations)

    if processed_user_stat_ids:
        user_stat_query = user_stat_query.filter(id__in=processed_user_stat_ids)

    processed_product_stat_ids = save_product_stats(date)

    stock_relations = {
        stock_id: stock_stat_id
        for stock_stat_id, stock_id in stock_stat_query.values_list("id", "stock_id")
    }
    user_relations = {
        user_id: user_stat_id
        for user_stat_id, user_id in user_stat_query.values_list("id", "user_id")
    }

    if not stock_relations or not user_relations:
        logger.error("Not fount stock or user stats!")
        return

    UserTransactionsStat.objects.filter(date=date).delete()
    save_transaction_stats(
        date=date,
        stock_relations=stock_relations,
        user_relations=user_relations
    )

    product_stat_query = ProductStat.objects.all()
    if processed_product_stat_ids:
        product_stat_query = product_stat_query.filter(id__in=processed_product_stat_ids)

    product_relations = {
        product_id: product_stat_id
        for product_stat_id, product_id in product_stat_query.values_list("id", "product_id")
    }
    if not product_relations:
        logger.error("Not found product relations!")
        return

    PurchaseStat.objects.filter(date=date).delete()
    save_purchase_stats(
        date,
        user_relations=user_relations,
        product_relations=product_relations,
        stock_relations=stock_relations
    )


def save_stock_group_stats(filter_type: str, months: list[datetime] = None,
                           start: datetime = None, end: datetime = None, **filters):
    grouping_filters = {}
    if filter_type == StockGroupStat.StatType.month:
        assert months
        grouping_filters["months"] = months
    else:
        assert start and end
        grouping_filters["start_date"] = start
        grouping_filters["end_date"] = end

    stocks_stats = get_stock_grouped_stats(stat_type=filter_type, **grouping_filters)

    stat_groups = {
        (getattr(stat_group, "stock_stat_id"), stat_group.date): stat_group
        for stat_group in (
            StockGroupStat.objects.filter(stat_type=filter_type, **filters)
        )
    }

    to_create = []
    to_update = []
    update_fields = set()
    processed = set()

    for data in stocks_stats:
        item_data = stock_group_builder.build_dict(data)
        check_key = (item_data["stock_stat_id"], item_data["date"])

        if check_key in processed:
            continue

        stat_group = stat_groups.get(check_key)

        if stat_group:
            for field, value in item_data.items():
                setattr(stat_group, field, value)
                update_fields.add(field)

            to_update.append(stat_group)
            processed.add(check_key)
            continue

        to_create.append(StockGroupStat(**item_data))
        processed.add(check_key)

    if to_update:
        StockGroupStat.objects.bulk_update(to_update, fields=update_fields)

    if to_create:
        try:
            StockGroupStat.objects.bulk_create(to_create)
        except Exception as e:
            print(stat_groups)
            raise e


def save_stock_group_for_month(date):
    save_stock_group_stats(
        filter_type=StockGroupStat.StatType.month,
        months=[date],
        date__month=date.month,
        date__year=date.year
    )


def save_stock_group_for_day(date):
    save_stock_group_stats(
        filter_type=StockGroupStat.StatType.day,
        start=date,
        end=date,
        date=date
    )
