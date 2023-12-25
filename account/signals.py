from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import DealerProfile, Wallet


@receiver(post_save, sender=DealerProfile)
def create_dealer_relations(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.get_or_create(dealer=instance)
