from datetime import datetime
from logging import getLogger

from django.db import models
from django.db.models import functions

from account.models import MyUser
from general_service.models import City, Stock
from one_c.models import MoneyDoc
from order.models import MyOrder
from product.models import AsiaProduct

from .models import UserTransactionsStat, PurchaseStat, UserStat, ProductStat, StockStat, CityStat, StockGroupStat
from .utils import Builder, get_stock_grouped_stats

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


def save_transaction_stats(date):
    transactions = MoneyDoc.objects.filter(
        is_active=True,
        created_at__date=date,
        user__in=models.Subquery(UserStat.objects.values("user_id")),
        cash_box__stock__in=models.Subquery(StockStat.objects.values("stock_id"))
    )

    if not transactions.exists():
        logger.error(f"Not found transactions for date {date}")
        return

    stock_relations = {
        stock_id: stock_stat_id
        for stock_stat_id, stock_id in (
            StockStat.objects
            .filter(stock__in=transactions.values("cash_box__stock_id"))
            .values_list("id", "stock_id")
        )
    }
    user_relations = {
        user_id: user_stat_id
        for user_stat_id, user_id in (
            UserStat.objects
            .filter(user__in=models.Subquery(transactions.values("user_id")))
            .values_list("id", "user_id")
        )
    }

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


def save_purchase_stats(date):
    purchases = MyOrder.objects.filter(
        released_at__date=date,
        status__in=("success", "sent"),
        is_active=True,
        author__user__in=models.Subquery(UserStat.objects.values("user_id")),
        stock__in=models.Subquery(StockStat.objects.values("stock_id")),
        order_products__ab_product__in=models.Subquery(ProductStat.objects.values("product_id"))
    )
    if not purchases.exists():
        logger.error(f"Not found purchases for date {date}")
        return

    stock_relations = {
        stock_id: stock_stat_id
        for stock_stat_id, stock_id in (
            StockStat.objects
            .filter(stock__in=purchases.values("stock_id"))
            .values_list("id", "stock_id")
        )
    }
    user_relations = {
        user_id: user_stat_id
        for user_stat_id, user_id in (
            UserStat.objects
            .filter(user__in=models.Subquery(purchases.values("author__user_id")))
            .values_list("id", "user_id")
        )
    }

    product_relations = {
        product_id: product_stat_id
        for product_stat_id, product_id in (
            ProductStat.objects
            .filter(product__in=models.Subquery(purchases.values("order_products__ab_product_id")))
            .values_list("id", "product_id")
        )
    }

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


def collect_city_stats():
    city_queryset = City.objects.only("id", "title", "is_active").all()

    update_cities = city_queryset.filter(id__in=models.Subquery(CityStat.objects.values("city_id")))
    saved_city_stats = {
        getattr(city_stat, "city_id"): city_stat.id
        for city_stat in (
            CityStat.objects.only("id", "city_id")
            .filter(city__id__in=models.Subquery(city_queryset.values("id")))
        )
    }

    to_update_city_stats = [
        CityStat(
            id=saved_city_stats[city.id],
            title=city.title,
            is_active=city.is_active
        )
        for city in update_cities
    ]

    if to_update_city_stats:
        CityStat.objects.bulk_update(to_update_city_stats, fields=["title", "is_active"])

    new_cities = city_queryset.exclude(id__in=models.Subquery(CityStat.objects.values("city_id")))
    new_city_stats = [
        CityStat(
            city_id=city.id,
            title=city.title,
            is_active=city.is_active
        )
        for city in new_cities
    ]
    if new_city_stats:
        CityStat.objects.bulk_create(new_city_stats)

    logger.info(f"Successfully collected cities")


def collect_stock_stats():
    stock_queryset = Stock.objects.only("id", "city_id", "title", "address", "is_active").all()

    update_stocks = stock_queryset.filter(id__in=models.Subquery(StockStat.objects.values("stock_id")))
    city_relations = {
        city_id: city_stat_id
        for city_stat_id, city_id in (
            CityStat.objects.filter(city__in=models.Subquery(stock_queryset.values("city_id")))
            .values_list("id", "city_id")
        )
    }
    saved_stock_stats = {
        getattr(stock_stat, "stock_id"): stock_stat.id
        for stock_stat in (
            StockStat.objects.only("id", "stock_id")
            .filter(stock__in=models.Subquery(stock_queryset.values("id")))
        )
    }

    to_update_stock_stats = [
        StockStat(
            id=saved_stock_stats[stock.id],
            title=stock.title,
            is_active=stock.is_active,
            address=stock.address,
            city_stat_id=city_relations[getattr(stock, "city_id")] if getattr(stock, "city_id") else None
        )
        for stock in update_stocks
    ]

    if to_update_stock_stats:
        StockStat.objects.bulk_update(to_update_stock_stats, fields=["title", "is_active", "address", "city_stat_id"])

    new_stocks = stock_queryset.exclude(id__in=models.Subquery(StockStat.objects.values("stock_id")))
    new_stock_stats = [
        StockStat(
            title=stock.title,
            is_active=stock.is_active,
            address=stock.address,
            city_stat_id=city_relations[getattr(stock, "city_id")] if getattr(stock, "city_id") else None
        )
        for stock in new_stocks
    ]
    if new_stock_stats:
        StockStat.objects.bulk_create(new_stock_stats)

    logger.info(f"Successfully collected stocks")


def collect_user_stats():
    users_queryset = (
        MyUser.objects.only("id", "email", "name")
        .select_related("dealer_profile")
        .filter(status="dealer", dealer_profile__isnull=False)
    )

    update_users = users_queryset.filter(id__in=models.Subquery(UserStat.objects.values("user_id")))
    city_relations = {
        city_id: city_stat_id
        for city_stat_id, city_id in (
            CityStat.objects.filter(city__in=models.Subquery(users_queryset.values("dealer_profile__village__city_id")))
            .values_list("id", "city_id")
        )
    }

    saved_user_stats = {
        getattr(user_stat, "user_id"): user_stat.id
        for user_stat in (
            UserStat.objects.only("id", "user_id")
            .filter(user__in=models.Subquery(users_queryset.values("id")))
        )
    }

    to_update_user_stats = [
        UserStat(
            id=saved_user_stats[user.id],
            name=user.name,
            email=user.email,
            city_stat_id=city_relations[getattr(user.dealer_profile.village, "city_id")]
            if getattr(user.dealer_profile, "village")
            else None
        )
        for user in update_users
    ]

    if to_update_user_stats:
        UserStat.objects.bulk_update(to_update_user_stats, fields=["name", "email", "city_stat_id"])

    new_users = users_queryset.exclude(id__in=models.Subquery(UserStat.objects.values("user_id")))
    new_user_stats = [
        UserStat(
            user_id=user.id,
            name=user.name,
            email=user.email,
            city_stat_id=city_relations[getattr(user.dealer_profile.village, "city_id")]
            if getattr(user.dealer_profile, "village")
            else None
        )
        for user in new_users
    ]
    if new_user_stats:
        UserStat.objects.bulk_create(new_user_stats)

    logger.info(f"Successfully collected users")


def collect_product_stats(date: datetime = None):
    query = {}
    if date:
        query["order_products__order__created_at__date"] = date.date()

    product_queryset = AsiaProduct.objects.filter(order_products__isnull=False, **query)

    update_products = product_queryset.filter(id__in=models.Subquery(ProductStat.objects.values("product_id")))
    saved_product_stats = {
        getattr(product_stat, "product_id"): product_stat.id
        for product_stat in (
            ProductStat.objects.only("id", "product_id")
            .filter(product__in=models.Subquery(product_queryset.values("id")))
        )
    }

    to_update_product_stats = [
        ProductStat(
            id=saved_product_stats[product.id],
            title=product.title,
            vendor_code=product.vendor_code,
            category_id=getattr(product, "category_id", None),
            collection_id=getattr(product, "collection_id", None)
        )
        for product in update_products.order_by("id").distinct("id")
    ]

    if to_update_product_stats:
        ProductStat.objects.bulk_update(
            to_update_product_stats,
            fields=["title", "vendor_code", "category_id", "collection_id"]
        )

    new_products = product_queryset.exclude(id__in=models.Subquery(ProductStat.objects.values("product_id")))
    new_product_stats = [
        ProductStat(
            product=product,
            title=product.title,
            vendor_code=product.vendor_code,
            category_id=getattr(product, "category_id", None),
            collection_id=getattr(product, "collection_id", None)
        )
        for product in new_products.order_by("id").distinct("id")
    ]
    if new_product_stats:
        ProductStat.objects.bulk_create(new_product_stats)

    logger.info(f"Successfully collected products")


def collects_stats_for_date(date: datetime):
    date = date.date()
    UserTransactionsStat.objects.filter(date=date).delete()
    save_transaction_stats(date=date)

    PurchaseStat.objects.filter(date=date).delete()
    save_purchase_stats(date)


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
