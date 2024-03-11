from django.db.models import Sum

from absklad_commerce.celery import app
from account.models import Notification, CRMNotification, DealerProfile, MyUser
from django.utils import timezone

from crm_general.models import AutoNotification, ProductRecommendation
from crm_general.utils import create_notifications_for_users
from product.models import ProductCount
from promotion.models import Banner


@app.task
def create_notifications():
    """
    Create every notification for user
    """
    naive_time = timezone.localtime().now()
    crn_time = timezone.make_aware(naive_time)
    crm_notifs = CRMNotification.objects.filter(dispatch_date__lte=crn_time, is_pushed=False, status='notif')
    update_notifs = []
    if crm_notifs:
        for notif in crm_notifs:
            create_notifications_for_users(crm_status=notif.status)
            notif.is_pushed = True
            update_notifs.append(notif)
    CRMNotification.objects.bulk_update(update_notifs, ['is_pushed'])


@app.task
def set_banner_false():
    naive_time = timezone.localtime().now()
    current_date = timezone.make_aware(naive_time)
    banners = Banner.objects.filter(is_active=True, end_time__month=current_date.month,
                                    end_time__day=current_date.day, end_time__year=current_date.year)
    for banner in banners:
        if banner.end_time < current_date:
            banner.is_active = False
            banner.save()


@app.task
def set_banner_true():
    naive_time = timezone.localtime().now()
    current_date = timezone.make_aware(naive_time)
    banners = Banner.objects.filter(is_active=False, start_time__month=current_date.month,
                                    start_time__day=current_date.day, start_time__year=current_date.year)
    for banner in banners:
        if banner.start_time <= current_date:
            banner.is_active = True
            banner.save()


@app.task
def create_birthday_recommend_notifications():
    naive_time = timezone.localtime().now()
    current_date = timezone.make_aware(naive_time)
    birthday_boys = MyUser.objects.filter(status='dealer', dealer_profile__birthday__month=current_date.month,
                                          dealer_profile__birthday__day=current_date.day)
    if birthday_boys:
        birthday_notification = AutoNotification.objects.filter(status='birthday').first()
        notifications_to_create = []
        if birthday_notification:
            for birthday_boy in birthday_boys:
                notifications_to_create.append(Notification(
                    user=birthday_boy,
                    status='birthday',
                    title=birthday_notification.title,
                    description=birthday_notification.text
                ))
            Notification.objects.bulk_create(notifications_to_create)

    users_to_recommend = ProductRecommendation.objects.filter(notification_created=False).distinct('user')
    if users_to_recommend:
        notification = AutoNotification.objects.filter(status='recommendation').first()
        recommendations_to_update = []
        if notification:
            nots_to_create = []
            total_product_count = 0
            for user_to_recommend in users_to_recommend:
                recommendations = ProductRecommendation.objects.filter(notification_created=False,
                                                                       user=user_to_recommend.user)
                for recommendation in recommendations:
                    product_count = ProductCount.objects.filter(product_id=recommendation.product.id).aggregate(
                        total_count_crm=Sum('count_crm')
                    )
                    if product_count['total_count_crm'] >= 1 and recommendation.product.is_active:
                        total_product_count += product_count['total_count_crm']
                        recommendation.notification_created = True
                        recommendations_to_update.append(recommendation)
                if total_product_count >= 1:
                    ProductRecommendation.objects.filter(user=user_to_recommend.user,
                                                         notification_created=True).delete()
                    nots_to_create.append(Notification(
                        user=user_to_recommend.user,
                        status='recommendation',
                        title=notification.title,
                        description=notification.text,
                        is_pushed=True
                    ))
                Notification.objects.bulk_create(nots_to_create)
                ProductRecommendation.objects.bulk_update(recommendations_to_update, ['notification_created'])
