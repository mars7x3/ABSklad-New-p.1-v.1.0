from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from one_c.models import MoneyDoc
from order.models import OrderProduct

from .tasks import update_dealer_kpi_plan_done, update_dealer_kpi_plan_product_done


@receiver(post_save, sender=MoneyDoc)
def on_save_money_doc(sender, instance, created, **kwargs):
    # TODO: call with delay
    update_dealer_kpi_plan_done(user_id=getattr(instance, 'user_id'))


@receiver(post_save, sender=OrderProduct)
def on_save_order_product(sender, instance, created, **kwargs):
    # TODO: call with delay
    update_dealer_kpi_plan_product_done(
        user_id=getattr(instance.order.dealer, "user_id"),
        product_id=getattr(instance, "ab_product_id"),
        city_id=getattr(instance.order.stock, "city_id")
    )
