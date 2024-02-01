import math
import logging
from typing import Callable

from dateutil.relativedelta import relativedelta
from django.db.models import F, Q, Count, Value, Case, When, Sum, FloatField, ExpressionWrapper, DecimalField, QuerySet
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from account.models import DealerStatus, DealerProfile, CRMNotification, MyUser, Notification
from order.models import MyOrder


def today_on_true(field_value):
    return timezone.now().date() if field_value and field_value == 'true' else None


def string_datetime_datetime(datetime_string: str, datetime_format: str = "%Y-%m-%d %H:%M:%S"):
    try:
        date = timezone.datetime.strptime(datetime_string, datetime_format)
        return timezone.make_aware(date)
    except Exception as e:
        logging.error(e)
        raise ValidationError(detail="Wrong format of date %s " % datetime_string)


def string_date_to_date(date_string: str, date_format: str = "%Y-%m-%d"):
    return string_datetime_datetime(date_string, date_format).date()


def list_of_date_stings(date_format: str = "%Y-%m-%d", cast: Callable = None):
    def format_dates(dates_string):
        collected = []
        for query in dates_string.split(','):
            date_str = query.strip()
            if not date_str:
                continue

            date = string_date_to_date(date_str, date_format)
            if cast:
                date = cast(date)

            collected.append(date)

        return collected
    return format_dates


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


def change_dealer_profile_status_after_deactivating_dealer_status(dealers: QuerySet[DealerProfile]):
    base_dealer_status = DealerStatus.objects.filter(discount=0).first()
    for dealer in dealers:
        dealer.dealer_status = base_dealer_status
        dealer.save()


def create_notifications_for_users(crm_status, link_id=None):
    if crm_status == 'notif':
        crm_notif = CRMNotification.objects.filter(status=crm_status).first()
    else:
        crm_notif = CRMNotification.objects.filter(status=crm_status, link_id=link_id).first()

    if crm_notif:
        notifications_to_create = []
        dealer_profiles = crm_notif.dealer_profiles.all()
        dealer_profile_ids = [dealer_profile.id if isinstance(dealer_profile, DealerProfile) else dealer_profile for
                              dealer_profile in dealer_profiles]
        users = MyUser.objects.filter(dealer_profile__id__in=dealer_profile_ids)
        if crm_notif.image:
            image_full_url = str(crm_notif.image.url).split('/')[-2:]
            image_url = '/'.join(image_full_url)
        else:
            image_url = None
        for user in users:
            notification_data = {
                'user': user,
                'title': crm_notif.title,
                'description': crm_notif.description,
                'status': crm_notif.status,
                'link_id': link_id,
                'image': image_url
            }
            notifications_to_create.append(notification_data)

        notification_to_create = [Notification(**n) for n in notifications_to_create]
        Notification.objects.bulk_create(notification_to_create)
        crm_notif.is_pushed = True
        crm_notif.save()
        print('Discount notifications were created')
