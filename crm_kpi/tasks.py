import logging
from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.db import transaction, models
from django.utils import timezone

from absklad_commerce.celery import app
from account.models import MyUser
from order.models import OrderProduct
from product.models import AsiaProduct, ProductPrice

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
    current_month = current_date.month
    last_month = current_date - relativedelta(months=1)
    last_three_month = timezone.now() - relativedelta(months=3)
    users = MyUser.objects.filter(status='dealer',
                                  dealer_profile__orders__isnull=False,
                                  dealer_profile__orders__created_at__gte=last_three_month,
                                  dealer_profile__orders__order_products__isnull=False).distinct()

    last_kpi = DealerKPI.objects.filter(month__month=last_month.month, month__year=current_date.year).first()
    if last_kpi:
        pds_percent = last_kpi.per_cent_pds / 100
        tmz_percent = last_kpi.per_cent_tmz / 100
        last_kpi_percent_pds = last_kpi.per_cent_pds
        last_kpi_percent_tmz = last_kpi.per_cent_tmz

    else:
        pds_percent = 0.25
        tmz_percent = 0.25
        last_kpi_percent_pds = 25
        last_kpi_percent_tmz = 25
    created_dealer_kpi = DealerKPI.objects.filter(month__month=current_month,
                                                  month__year=current_date.year).values_list('user__id', flat=True)

    update_dealer_kpi_pds = []

    for user in users:
        if user.id not in created_dealer_kpi:
            with transaction.atomic():
                user_tmz_data = get_tmz_of_user_for_kpi(3, user.id)
                total_pds = 0

                if user_tmz_data:
                    new_kpi = DealerKPI.objects.create(
                        user=user,
                        month=current_date,
                        is_confirmed=False,
                        per_cent_pds=last_kpi_percent_pds,
                        per_cent_tmz=last_kpi_percent_tmz
                    )

                    dealer_kpi_products = []

                    for tmz_data in user_tmz_data:
                        if tmz_data['total_count'] is not None:

                            total_count = tmz_data['total_count']
                            if total_count > 3:
                                avg_total_count = total_count / 3
                            else:
                                avg_total_count = total_count
                            increase_count = int(avg_total_count) * tmz_percent
                            increased_total_count = round(int(avg_total_count) + increase_count)

                            product = AsiaProduct.objects.get(id=tmz_data['order_products__ab_product__id'])

                            price_type = user.dealer_profile.price_type
                            city = user.dealer_profile.village.city
                            if price_type:
                                product_price = ProductPrice.objects.filter(price_type=price_type,
                                                                            product=product,
                                                                            d_status__discount=0).first().price
                            else:
                                product_price = ProductPrice.objects.filter(city=city,
                                                                            product=product,
                                                                            d_status__discount=0).first().price
                            total_price = increased_total_count * product_price
                            total_pds += int(total_price)

                            dealer_kpi_products.append(
                                DealerKPIProduct(
                                    kpi=new_kpi,
                                    product=product,
                                    count=increased_total_count,
                                    sum=total_price
                                )
                            )
                    DealerKPIProduct.objects.bulk_create(dealer_kpi_products)
                    increase_amount = int(total_pds) * pds_percent
                    total_pds = round(int(total_pds) + increase_amount)
                    kpi = DealerKPI.objects.get(id=new_kpi.id)
                    kpi.pds = total_pds
                    update_dealer_kpi_pds.append(kpi)
                    print(f'Created new KPI {kpi.id} for user {user.id}. date: {current_date}')

        else:
            print(f'DealerKPI for user id {user.id} id being skipped as it was already created. {current_date}')
    DealerKPI.objects.bulk_update(update_dealer_kpi_pds, ['pds'])


@app.task
def confirm_dealer_kpis():
    current_date = timezone.now()
    unconfirmed_dealer_kpis = DealerKPI.objects.filter(month__month=current_date.month,
                                                       month__year=current_date.year,
                                                       is_confirmed=False)
    update_data = []
    for kpi in unconfirmed_dealer_kpis:
        kpi.is_confirmed = True
        update_data.append(kpi)
    DealerKPI.objects.bulk_update(update_data, ['is_confirmed'])
    print(f'Dealer KPI confirmed count {len(update_data)}')