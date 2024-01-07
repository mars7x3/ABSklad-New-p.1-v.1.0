import logging

from dateutil.relativedelta import relativedelta
from django.db.models import F, Q, Count, Value, Case, When, Sum, DecimalField
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from order.models import MyOrder

from .models import DealerKPIPlan, ProductToBuy, ProductToBuyCount


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


def create_dealer_kpi_plans(target_month: int, months: int):
    assert 0 < months < 13
    months_ago = timezone.now() - relativedelta(months=months)
    orders = (
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
            count=Case(
                When(
                    products_count__gt=Value(months),
                    then=F("products_count") / Value(months)
                ),
                default=Value(1)
            ),
            spend_amount=Case(
                When(
                    spend_amount_sum__isnull=False,
                    spend_amount_sum__gt=months,
                    then=F("spend_amount_sum") / Value(months)
                ),
                When(
                    spend_amount_sum__isnull=False,
                    spend_amount_sum__lte=months,
                    then=F("spend_amount_sum")
                ),
                default=Value(0.0),
                output_field=DecimalField()
            )
        )
    )

    new_plans = []
    processed_dealer_ids = set()
    collected_products_to_buy = {}
    collected_product_counts = {}

    for order in orders:
        dealer_id = order["dealer_id"]
        if dealer_id not in processed_dealer_ids:
            new_plan = DealerKPIPlan(
                dealer_id=dealer_id,
                target_month=target_month,
                spend_amount=order["spend_amount"]
            )
            new_plans.append(new_plan)

        product_id = order["product_id"]
        if dealer_id not in collected_products_to_buy:
            collected_products_to_buy[dealer_id] = []

        collected_products_to_buy[dealer_id].append(product_id)

        if product_id not in collected_product_counts:
            collected_product_counts[product_id] = []

        collected_product_counts[product_id].append(dict(city_id=order["city_id"], count=order["count"]))
        processed_dealer_ids.add(dealer_id)

    if new_plans:
        kpi_plans = DealerKPIPlan.objects.bulk_create(new_plans)

        new_products_to_buy = [
            ProductToBuy(kpi_plan=kpi_plan, product_id=product_id)
            for kpi_plan in kpi_plans
            for product_id in collected_products_to_buy.get(getattr(kpi_plan, "dealer_id")) or []
        ]

        saved_products = ProductToBuy.objects.bulk_create(new_products_to_buy) if new_products_to_buy else []
        new_product_counts = [
            ProductToBuyCount(product_to_buy=saved_product, **purchase_data)
            for saved_product in saved_products
            for purchase_data in collected_product_counts.get(getattr(saved_product, "product_id")) or []
        ]

        if new_product_counts:
            ProductToBuyCount.objects.bulk_create(new_product_counts)


def create_dealer_kpi_to_next_month():
    create_dealer_kpi_plans(target_month=(timezone.now() + relativedelta(months=1)).month, months=3)
