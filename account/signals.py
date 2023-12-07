
from django.db.models.signals import post_save
from django.dispatch import receiver

from account.models import MyUser, Notification


@receiver(post_save, sender=MyUser)
def password_hash(sender, instance, created, **kwargs):
    if created and not instance.is_superuser:
        Notification.objects.create(
            user=instance,
            status='notif',
            title='Hello!',
            description='This is ASIA BRAND!'
        )
