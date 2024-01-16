import logging

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from account.models import MyUser
from order.models import MyOrder
from product.models import AsiaProduct
from .models import DealerKPI, DealerKPIProduct
from .utils import get_tmz_of_user_for_kpi

logger = logging.getLogger('tasks_management')


def create_dealer_kpi():
    current_date = timezone.now().date()
    last_month = current_date - relativedelta(months=1)
    last_three_month = timezone.now() - relativedelta(months=3)

    users = MyUser.objects.filter(dealer_profile__orders__created_at__gte=last_three_month).distinct()
    last_kpi = DealerKPI.objects.filter(month=last_month).first()
    # pds_percent = last_kpi.per_cent_pds
    # tmz_percent = last_kpi.per_cent_tmz
    increase_percentage = 0.25

    created_dealer_kpi = DealerKPI.objects.filter(month=current_date).values_list('user__id', flat=True)

    for user in users:
        if user.id in created_dealer_kpi:
            print(f'DealerKPI for user id {user.id} id being skipped as it was already created')
            continue
        else:
            new_kpi = DealerKPI.objects.create(
                user=user,
                month=current_date
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
                        increase_count = int(avg_total_count) * increase_percentage
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

                increase_amount = int(total_pds) * increase_percentage
                total_pds = round(int(total_pds) + increase_amount)
                print('total_pds: ', total_pds)
                kpi = DealerKPI.objects.get(id=new_kpi.id)
                kpi.pds = total_pds
                kpi.save()
