from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.timezone import now

from account.models import DealerStatus
from general_service.models import City, PriceType
from one_c.models import MoneyDoc
from order.models import OrderProduct
from product.models import AsiaProduct

from .tasks import create_dealer_kpi_plan_stats, create_dealer_kpi_plan_product_stats
from .utils import remove_product_from_banner_story


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
    if instance.is_active is False:
        remove_product_from_banner_story(instance)
        return

    d_status_qty = DealerStatus.objects.all().count()
    general_prices_qty = (
        # Count of statuses in active cities
        d_status_qty * City.objects.filter(is_active=True).count()
        +
        # Count of statuses with active price types
        d_status_qty * PriceType.objects.filter(is_active=True).count()
    )

    if (
        general_prices_qty <= instance.prices.all().count() and not instance.prices.filter(price=0).exists()
        and
        instance.description and len(instance.description) > 100
        and
        instance.cost_prices.filter(is_active=True).exists()
        and
        instance.images.exists()
        and
        instance.sizes.exists()
    ):
        AsiaProduct.objects.filter(pk=instance.pk).update(is_active=True)
    else:
        AsiaProduct.objects.filter(pk=instance.pk).update(is_active=False)
