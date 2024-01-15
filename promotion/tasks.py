import logging

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from account.models import MyUser
from order.models import MyOrder
from .models import DealerKPI, DealerKPIProduct
from .utils import get_tmz_of_user_for_kpi

logger = logging.getLogger('tasks_management')


def create_dealer_kpi():
    current_date = timezone.now().date()
    last_month = current_date - relativedelta(months=1)

    user_tmz_data = get_tmz_of_user_for_kpi(3)
    user_ids = [user['author__user'] for user in user_tmz_data]
    users = MyUser.objects.filter(id__in=user_ids)

    last_kpi = DealerKPI.objects.filter(month=last_month)
    pds_percent = last_kpi.per_cent_pds
    tmz_percent = last_kpi.per_cent_tmz

    for user in users:

        created_dealer_kpi = DealerKPI.objects.filter(user=user, month=current_date)
        dealer_kpis_to_create = []
        dealer_tmz_kpis_to_create = []
        if created_dealer_kpi:
            # logger.info(f'DealerKPI for user id {active_user.id} id being skipped as it was already created')
            print(f'DealerKPI for user id {user.id} id being skipped as it was already created')
            continue

        elif user not in created_dealer_kpi:
            dealer_kpis_to_create.append(
                DealerKPI(
                    user=user,
                    pds=100000
                )
            )

            dealer_tmz_kpis_to_create.append(
                DealerKPIProduct(
                    kpi='kpi',
                    product='product',
                    count='count',
                )
            )