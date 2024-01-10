import math
import logging

from dateutil.relativedelta import relativedelta
from django.db.models import F, Q, Count, Value, Case, When, Sum, FloatField, ExpressionWrapper, DecimalField
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from order.models import MyOrder


def today_on_true(field_value):
    return timezone.now().date() if field_value and field_value == 'true' else None


def string_date_to_date(date_string: str):
    try:
        date = timezone.datetime.strptime(date_string, "%Y-%m-%d")
        return timezone.make_aware(date).date()
    except Exception as e:
        logging.error(e)
        raise ValidationError(detail="Wrong format of date %s " % date_string)


def convert_bool_string_to_bool(bool_str: str) -> bool:
    return bool_str.lower() == "true"


def get_motivation_done(dealer):
    motivations_data = []
    motivations = dealer.motivations.filter(is_active=True)

    for motivation in motivations:
        motivation_data = {
            "title": motivation.title,
            "start_date": motivation.start_date,
            "end_date": motivation.end_date,
            "is_active": motivation.is_active,
            "conditions": []
        }

        conditions = motivation.conditions.all()
        orders = dealer.orders.filter(
            is_active=True, status__in=['sent', 'sent', 'success', 'wait'],
            paid_at__gte=motivation.start_date)

        for condition in conditions:
            condition_data = {
                "status": condition.status,
                "presents": []
            }

            if condition.status == 'category':
                condition_data["condition_cats"] = []
                condition_cats = condition.condition_cats.all()
                for condition_cat in condition_cats:
                    category_data = {
                        "count": condition_cat.count,
                        "category": condition_cat.category.id,
                        "category_title": condition_cat.category.title
                    }
                    condition_data["condition_cats"].append(category_data)
                    total_count = sum(
                        order_products.count
                        for order in orders
                        for order_products in order.order_products.filter(category=condition_cat.category)
                    )
                    condition_data['done'] = total_count
                    condition_data['per'] = round(total_count * 100 / condition_cat.count)

            elif condition.status == 'product':
                condition_data["condition_prods"] = []
                condition_prods = condition.condition_prods.all()
                for condition_prod in condition_prods:
                    product_data = {
                        "count": condition_prod.count,
                        "product": condition_prod.product.id,
                        "product_title": condition_prod.product.title
                    }
                    condition_data["condition_prods"].append(product_data)

                    total_count = sum(
                        order_products.count
                        for order in orders
                        for order_products in order.order_products.filter(ab_product=condition_prod.product)
                    )
                    condition_data['done'] = total_count
                    condition_data['per'] = round(total_count * 100 / condition_prod.count)

            elif condition.status == 'money':
                condition_data["money"] = condition.money
                total_count = sum(orders.values_list('price', flat=True))
                condition_data['done'] = total_count
                condition_data['per'] = round(total_count * 100 / condition.money)

            presents = condition.presents.all()
            for p in presents:
                present_data = {
                    "status": p.status,
                    "money": p.money,
                    "text": p.text
                }

                condition_data["presents"].append(present_data)

            motivation_data["conditions"].append(condition_data)

        motivations_data.append(motivation_data)

    return motivations_data


def round_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.ceil(n * multiplier) / multiplier


def collect_orders_data_for_kpi_plan(check_months_ago, increase_threshold: float):
    assert 0 < check_months_ago < 13
    months_ago = timezone.now() - relativedelta(months=check_months_ago)

    return (
        MyOrder.objects.filter(
            status__in=("wait", "sent", "paid", "success"),
            created_at__date__gte=months_ago
        )
        .values(dealer_id=F("author__user_id"))
        .annotate(
            product_id=F("order_products__ab_product_id"),
            city_id=F("stock__city_id"),
            products_count=Count("order_products__count"),
            spend_amount_sum=Sum(
                "author__user__money_docs__amount",
                filter=Q(
                    author__user__money_docs__is_active=True,
                    author__user__money_docs__created_at__date__gte=months_ago
                )
            )
        )
        .annotate(
            avg_count=Case(
                When(
                    products_count__gt=Value(check_months_ago),
                    then=F("products_count") / Value(check_months_ago)
                ),
                default=Value(1)
            ),
            avg_spend_amount=Case(
                When(
                    spend_amount_sum__isnull=False,
                    spend_amount_sum__gt=check_months_ago,
                    then=F("spend_amount_sum") / Value(check_months_ago)
                ),
                When(
                    spend_amount_sum__isnull=False,
                    spend_amount_sum__lte=check_months_ago,
                    then=F("spend_amount_sum")
                ),
                default=Value(0.0),
                output_field=FloatField()
            )
        )
        .annotate(
            spend_amount=ExpressionWrapper(
                F("avg_spend_amount") + (F("avg_spend_amount") * Value(increase_threshold)),
                output_field=DecimalField()
            )
        )
    )
