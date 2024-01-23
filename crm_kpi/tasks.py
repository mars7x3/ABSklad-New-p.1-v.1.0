import logging
from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.db import transaction, models
from django.utils import timezone

from absklad_commerce.celery import app
from account.models import MyUser
from order.models import OrderProduct
from product.models import AsiaProduct

from .models import DealerKPI, DealerKPIProduct, ManagerKPI, ManagerKPISVD
from .utils import get_tmz_of_user_for_kpi

logger = logging.getLogger('tasks_management')


@app.task()
def create_kpi():
    create_dealer_kpi.delay()
    create_manager_kpi.delay()


@app.task()
def create_manager_kpi():
    today = timezone.now()
    current_date = datetime(month=today.month, year=today.year, day=1).date()
    month_ago = today - relativedelta(months=1)
    three_month_ago = today - relativedelta(months=3)

    saved_manager_ids = ManagerKPI.objects.filter(month__month=today.month, month__year=today.year).values("manager_id")

    managers_queryset = MyUser.objects.filter(~models.Q(id__in=models.Subquery(saved_manager_ids)), status='manager')
    managers = (
        managers_queryset
        .values("id")
        .annotate(
            akb=models.Count(
                "dealer_profiles__user_id",
                distinct=True,
                filter=models.Q(
                    dealer_profiles__orders__isnull=False,
                    dealer_profiles__orders__created_at__month=month_ago.month
                )
            )
        )
    )

    new_managers_kpi = [
        ManagerKPI(manager_id=manager["id"], akb=manager["akb"], month=current_date)
        for manager in managers
    ]

    if not new_managers_kpi:
        logger.error(f"Not found new managers for ManagerKPI saving date: {current_date}")
        return

    saved_manager_kpi_objs = {
        getattr(manager_kpi, "manager_id"): manager_kpi
        for manager_kpi in ManagerKPI.objects.bulk_create(new_managers_kpi)
    }

    products = (
        OrderProduct.objects.filter(
            order__author__managers__id__in=saved_manager_kpi_objs.keys(),
            order__created_at__gte=three_month_ago,
            order__status__in=['paid', 'sent', 'success', 'wait']
        )
        .values(manager_id=models.F('order__author__managers__id'), product_id=models.F('ab_product__id'))
        .annotate(total_count=models.Sum('count'))
    )
    new_managers_svd = [
        ManagerKPISVD(
            manager_kpi=saved_manager_kpi_objs[product["manager_id"]],
            product_id=product["product_id"],
            count=product["total_count"]
        )
        for product in products
        if product["manager_id"] in saved_manager_kpi_objs
    ]
    if new_managers_svd:
        ManagerKPISVD.objects.bulk_create(new_managers_svd)


@app.task()
def create_dealer_kpi():
    current_date = timezone.now().date()
    last_month = current_date - relativedelta(months=1)
    last_three_month = timezone.now() - relativedelta(months=3)
    users = MyUser.objects.filter(status='dealer',
                                  dealer_profile__orders__isnull=False,
                                  dealer_profile__orders__created_at__gte=last_three_month).distinct()

    last_kpi = DealerKPI.objects.filter(month__month=last_month.month).first()
    pds_percent = last_kpi.per_cent_pds / 100
    tmz_percent = last_kpi.per_cent_tmz / 100
    created_dealer_kpi = DealerKPI.objects.filter(month=current_date).values_list('user__id', flat=True)

    for user in users:
        if user.id not in created_dealer_kpi:
            with transaction.atomic():
                new_kpi = DealerKPI.objects.create(
                    user=user,
                    month=current_date,
                    per_cent_pds=last_kpi.per_cent_pds,
                    per_cent_tmz=last_kpi.per_cent_tmz
                )

                user_tmz_data = get_tmz_of_user_for_kpi(3, user.id)
                total_pds = 0
                if user_tmz_data is not None:
                    for tmz_data in user_tmz_data:
                        if tmz_data['total_count'] is not None:

                            total_count = tmz_data['total_count']
                            if total_count > 3:
                                avg_total_count = total_count / 3
                            else:
                                avg_total_count = total_count
                            increase_count = int(avg_total_count) * tmz_percent
                            increased_total_count = round(int(avg_total_count) + increase_count)

                            total_price = tmz_data['total_price']

                            total_pds += int(total_price)

                            product = AsiaProduct.objects.get(id=tmz_data['order_products__ab_product__id'])

                            DealerKPIProduct.objects.create(
                                kpi=new_kpi,
                                product=product,
                                count=increased_total_count,
                            )
                    increase_amount = int(total_pds) * pds_percent
                    total_pds = round(int(total_pds) + increase_amount)
                    kpi = DealerKPI.objects.get(id=new_kpi.id)
                    kpi.pds = total_pds
                    kpi.save()
        else:
            print(f'DealerKPI for user id {user.id} id being skipped as it was already created')


@app.task
def confirm_dealer_kpis():
    current_date = timezone.now()
    unconfirmed_dealer_kpis = DealerKPI.objects.filter(month__month=current_date.month, is_confirmed=False)
    for kpi in unconfirmed_dealer_kpis:
        kpi.is_confirmed = True
        kpi.save()
