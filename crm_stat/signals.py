from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserTransactionsStat, PurchaseStat
from .tasks import task_update_tx_stat_group, task_update_purchase_stat_group


@receiver(post_save, sender=UserTransactionsStat)
def on_update_tx_stat(sender, instance, created, **kwargs):
    task_update_tx_stat_group.delay(instance.id)


@receiver(post_save, sender=PurchaseStat)
def on_update_purchase_stat(sender, instance, created, **kwargs):
    task_update_purchase_stat_group.delay(instance.id)
