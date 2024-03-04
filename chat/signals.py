from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from chat.models import Chat


@receiver(post_save, sender=get_user_model())
def create_chat_for_dealer(sender, instance, created, **kwargs):
    if instance.is_dealer:
        Chat.objects.get_or_create(dealer=instance)
