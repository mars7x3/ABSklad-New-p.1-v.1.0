import logging
from pprint import pprint

from django.utils import timezone
from django.db.models import F, Q, Sum, Value, FloatField
from django.db.models.functions import Round
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError


def today_on_true(field_value):
    return now().date() if field_value and field_value == 'true' else None


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
    response_data = []

    for motivation in dealer.motivations.filter(is_active=True):
        motivation_data = {"title": motivation.title}

        for condition in motivation.conditions.all():
            match condition.status:
                case "category":
                    category_condition_data = condition.condition_cats.annotate(
                        status=Value(condition.status),
                        category_title=F("category__title"),
                        total_count=F("count"),
                        done_count=Sum(
                            "category__order_products__count",
                            filter=Q(
                                category__order_products__order__is_active=True,
                                category__order_products__order__status__in=(
                                    'Отправлено', 'Оплачено', 'Успешно', 'Ожидание'
                                ),
                                category__order_products__order__paid_at__gte=motivation.start_date
                            ),
                            output_field=FloatField()
                        ),
                        per=Round(
                            Sum(
                                "category__order_products__count",
                                filter=Q(
                                    category__order_products__order__is_active=True,
                                    category__order_products__order__status__in=(
                                        'Отправлено', 'Оплачено', 'Успешно', 'Ожидание'
                                    ),
                                    category__order_products__order__paid_at__gte=motivation.start_date
                                )
                            ) * Value(100) / F("count"),
                            precision=2,
                            output_field=FloatField()
                        )
                    ).values("category_title", "total_count", "done_count", "per")[0]

                    if not motivation_data.get("categories"):
                        motivation_data["categories"] = []

                    motivation_data["categories"].append(category_condition_data)

                case "product":
                    product_condition_data = condition.condition_prods.annotate(
                        status=Value(condition.status),
                        product_title=F("product__title"),
                        total_count=F("count"),
                        done_count=Sum(
                            "product__order_products__count",
                            filter=Q(
                                product__order_products__order__is_active=True,
                                product__order_products__order__status__in=(
                                    'Отправлено', 'Оплачено', 'Успешно', 'Ожидание'
                                ),
                                product__order_products__order__paid_at__gte=motivation.start_date
                            ),
                            output_field=FloatField()
                        ),
                        per=Round(
                            Sum(
                                "product__order_products__count",
                                filter=Q(
                                    product__order_products__order__is_active=True,
                                    product__order_products__order__status__in=(
                                        'Отправлено', 'Оплачено', 'Успешно', 'Ожидание'
                                    ),
                                    product__order_products__order__paid_at__gte=motivation.start_date
                                )
                            ) * Value(100) / F("count"),
                            precision=2,
                            output_field=FloatField()
                        )
                    ).values("product_title", "total_count", "done_count", "per")[0]

                    if not motivation_data.get("products"):
                        motivation_data["products"] = []

                    motivation_data["products"].append(product_condition_data)

                case 'money':
                    money_condition_data = (
                        dealer.orders.filter(is_active=True, aid_at__gte=motivation.start_date,
                                             status__in=['Отправлено', 'Оплачено', 'Успешно', 'Ожидание'])
                        .aggregate(
                            status=Value(condition.status),
                            total_amount=Value(condition.money),
                            done_amount=Sum("price", output_field=FloatField()),
                            per=Round(
                                Sum("price") * Value(100) / Value(condition.money),
                                precision=2,
                                output_field=FloatField()
                            )
                        )
                    )
                    money_condition_data["money"] = money_condition_data

            presents = []
            for present_data in condition.presents.values("status", "product", "money", "text"):
                present_data["money"] = float(present_data["money"])
                presents.append(present_data)

            motivation_data["presents"] = presents
            response_data.append(motivation_data)

        pprint(response_data)
        # return response_data
