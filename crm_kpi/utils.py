from dateutil.relativedelta import relativedelta
from django.db.models import Sum, F, IntegerField, Case, When, FloatField
from django.utils import timezone

from crm_kpi.models import DealerKPI
from order.models import MyOrder


def get_tmz_of_user_for_kpi(check_months, user_id):
    start_date = timezone.now() - relativedelta(months=check_months)

    user_order_products = MyOrder.objects.filter(
        author__user__id=user_id,
        created_at__gte=start_date,
        status__in=['paid', 'sent', 'success', 'wait']
    ).values(
        'author__user',
        'order_products__ab_product__id',
    ).annotate(
        total_count=Sum('order_products__count'),
        total_price=Sum('order_products__total_price'),
    )

    return user_order_products


def kpi_total_info(month):
    kpis = DealerKPI.objects.filter(
        month__month=month
    ).annotate(
        fact_total_pds=Sum("fact_pds", default=0),
        fact_total_tmz_count=Sum('kpi_products__fact_count', default=0),
        fact_total_tmz_sum=Sum('kpi_products__fact_sum', default=0),
        fact_avg_price=Sum(F('kpi_products__fact_sum') / F('kpi_products__fact_count'), output_field=FloatField(),
                           default=0),
        total_pds=Sum("pds", default=0),
        total_tmz_count=Sum('kpi_products__count', default=0),
        total_tmz_sum=Sum('kpi_products__sum', default=0),
        avg_price=Sum(F('kpi_products__sum') / F('kpi_products__count'), output_field=FloatField(), default=0)
    ).values_list('fact_total_pds', 'fact_total_tmz_count', 'fact_total_tmz_sum', 'fact_avg_price',
                  'total_pds', 'total_tmz_count', 'total_tmz_sum', 'avg_price')

    total_kpis = tuple(sum(x) for x in zip(*kpis))

    total_data = {
        'fact_total_pds': total_kpis[0],
        'fact_total_tmz_count': total_kpis[1],
        'fact_total_tmz_sum': total_kpis[2],
        'fact_avg_price': total_kpis[3],
        'total_pds': total_kpis[4],
        'total_tmz_count': total_kpis[5],
        'total_tmz_sum': total_kpis[6],
        'avg_price': total_kpis[7],
    }
    return total_data


