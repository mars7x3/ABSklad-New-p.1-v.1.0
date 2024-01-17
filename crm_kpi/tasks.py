import logging

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone

from absklad_commerce.celery import app
from account.models import MyUser
from product.models import AsiaProduct
from .models import DealerKPI, DealerKPIProduct
from .utils import get_tmz_of_user_for_kpi

logger = logging.getLogger('tasks_management')


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
    print('pds_percent: ', pds_percent)
    print('tmz_percent: ', tmz_percent)
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
                print('-------------------------------------------------------')
                print('user_tmz_data: ', user_tmz_data)
                if user_tmz_data is not None:
                    for tmz_data in user_tmz_data:
                        if tmz_data['total_count'] is not None:

                            total_count = tmz_data['total_count']
                            if total_count > 3:
                                avg_total_count = total_count / 3
                            else:
                                avg_total_count = total_count
                            print('total_count: ', total_count)
                            increase_count = int(avg_total_count) * tmz_percent
                            increased_total_count = round(int(avg_total_count) + increase_count)
                            print('increased_total_count: ', increased_total_count)

                            total_price = tmz_data['total_price']
                            print('total_price: ', total_price)

                            total_pds += int(total_price)

                            product = AsiaProduct.objects.get(id=tmz_data['order_products__ab_product__id'])

                            DealerKPIProduct.objects.create(
                                kpi=new_kpi,
                                product=product,
                                count=increased_total_count,
                            )
                            print('-------------------')
                    increase_amount = int(total_pds) * pds_percent
                    total_pds = round(int(total_pds) + increase_amount)
                    print('total_pds: ', total_pds)
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
