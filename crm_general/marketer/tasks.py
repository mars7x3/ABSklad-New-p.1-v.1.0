from absklad_commerce.celery import app
from account.models import Notification, CRMNotification
from django.utils import timezone

from crm_general.utils import create_notifications_for_users
from promotion.models import Banner


@app.task
def create_notifications():
    """
    Create every notification for user
    """
    crn_time = timezone.now()
    crm_notifs = CRMNotification.objects.filter(dispatch_date__lte=crn_time, is_pushed=False, status='notif')
    if crm_notifs:
        for notif in crm_notifs:
            create_notifications_for_users(crm_status=notif.status)


@app.task
def set_banner_false():
    current_date = timezone.now()
    banners = Banner.objects.filter(is_active=True, end_time__month=current_date.month,
                                    end_time__day=current_date.day, end_time__year=current_date.year)
    for banner in banners:
        if banner.end_time < current_date:
            banner.is_active = False
            banner.save()


@app.task
def set_banner_true():
    current_date = timezone.now()
    banners = Banner.objects.filter(is_active=False, start_time__month=current_date.month,
                                    start_time__day=current_date.day, start_time__year=current_date.year)
    for banner in banners:
        if banner.start_time <= current_date:
            banner.is_active = True
            banner.save()
