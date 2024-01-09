from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.timezone import now

from one_c.models import MoneyDoc
from order.models import OrderProduct

from .tasks import create_dealer_kpi_plan_stats, create_dealer_kpi_plan_product_stats


# @receiver(post_save, sender=MoneyDoc)
def on_save_money_doc(sender, instance, created, **kwargs):
    today = now()
    if instance.created_at.month != today.month or instance.created_at.year != today.year:
        return

    # TODO: call with delay
    create_dealer_kpi_plan_stats(
        user_id=getattr(instance, 'user_id'),
        target_month=today.month,
        target_year=today.year
    )


# @receiver(post_delete, sender=MoneyDoc)
def on_delete_money_doc(sender, instance, **kwargs):
    today = now()
    if instance.created_at.month != today.month or instance.created_at.year != today.year:
        return

    # TODO: call with delay
    create_dealer_kpi_plan_stats(
        user_id=getattr(instance, 'user_id'),
        target_month=today.month,
        target_year=today.year
    )


# @receiver(post_save, sender=OrderProduct)
def on_save_order_product(sender, instance, created, **kwargs):
    today = now()
    if instance.created_at.month != today.month or instance.created_at.year != today.year:
        return

    # TODO: call with delay
    create_dealer_kpi_plan_product_stats(
        user_id=getattr(instance.order.dealer, "user_id"),
        product_id=getattr(instance, "ab_product_id"),
        city_id=getattr(instance.order.stock, "city_id"),
        target_month=today.month,
        target_year=today.year
    )


# @receiver(post_delete, sender=OrderProduct)
def on_delete_order_product(sender, instance, **kwargs):
    today = now()
    if instance.created_at.month != today.month or instance.created_at.year != today.year:
        return

    # TODO: call with delay
    create_dealer_kpi_plan_product_stats(
        user_id=getattr(instance, 'user_id'),
        product_id=getattr(instance, "ab_product_id"),
        city_id=getattr(instance.order.stock, "city_id"),
        target_month=today.month,
        target_year=today.year
    )
