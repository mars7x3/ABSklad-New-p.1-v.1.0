from absklad_commerce.celery import app
from account.models import Notification
from django.utils import timezone


@app.task()
def create_notifications(notifications: list, image_url, dispatch_date):
    """
    Create every notification for user
    """
    print('worked')
    if dispatch_date <= timezone.now():
        notification_to_create = [Notification(**n) for n in notifications]
        nots = Notification.objects.bulk_create(notification_to_create)
        for notification in nots:
            notification.image = image_url
            notification.save()
