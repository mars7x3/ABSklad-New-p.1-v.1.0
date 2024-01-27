from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.timezone import now

from account.models import DealerStatus
from general_service.models import City, PriceType
from one_c.models import MoneyDoc
from order.models import OrderProduct
from product.models import AsiaProduct

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


@receiver(post_save, sender=AsiaProduct)
def check_product_before_activation(sender, instance, created, **kwargs):
    count = 0

    d_status_city_counts = DealerStatus.objects.all().count() * City.objects.filter(is_active=True).count()
    d_status_type_counts = DealerStatus.objects.all().count() * PriceType.objects.filter(is_active=True).count()
    final_price_count = d_status_city_counts + d_status_type_counts
    product_price_count = instance.prices.all().count()
    if final_price_count == product_price_count:
        count += 1

    cost_prices = instance.cost_prices.filter(price=0)
    if len(cost_prices) == 0:
        count += 1

    if len(instance.description) > 100:
        count += 1

    images = instance.images.first()
    if images:
        count += 1

    sizes = instance.sizes.first()
    if sizes:
        count += 1

    if instance.is_active:
        if count < 5:
            instance.is_active = False
            instance.save()

    if count == 5:
        instance.is_active = True
        instance.save()
