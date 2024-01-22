from django.db.models.signals import post_save
from django.dispatch import receiver

from one_c.from_crm import sync_product_crm_to_1c
from product.models import AsiaProduct


@receiver(post_save, sender=AsiaProduct)
def create_dealer_relations(sender, instance, created, **kwargs):
    sync_product_crm_to_1c(instance)


