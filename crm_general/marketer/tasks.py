from absklad_commerce.celery import app
from account.models import Notification
from django.utils import timezone

from promotion.models import Banner


@app.task()
def create_notifications(notifications: list, image_url, dispatch_date):
    """
    Create every notification for user
    """
    if dispatch_date <= timezone.now():
        notification_to_create = [Notification(**n) for n in notifications]
        nots = Notification.objects.bulk_create(notification_to_create)
        for notification in nots:
            notification.image = image_url
            notification.save()


@app.task()
def set_banner_false():
    current_date = timezone.now()
    banners = Banner.objects.filter(is_active=True, end_time__month=current_date.month,
                                    end_time__day=current_date.day, end_time__year=current_date.year)
    for banner in banners:
        if banner.end_time < current_date:
            banner.is_active = False
            banner.save()


@app.task()
def set_banner_true():
    current_date = timezone.now()
    banners = Banner.objects.filter(is_active=False, end_time__month=current_date.month,
                                    end_time__day=current_date.day, end_time__year=current_date.year)
    for banner in banners:
        if banner.start_time <= current_date:
            banner.is_active = True
            banner.save()
