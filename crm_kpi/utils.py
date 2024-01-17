from dateutil.relativedelta import relativedelta
from django.db.models import Sum, F, IntegerField, Case, When, FloatField
from django.utils import timezone

from account.models import MyUser
from crm_kpi.models import DealerKPI
from order.models import MyOrder, OrderProduct


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
        avg_price=Sum(F('kpi_products__sum') / F('kpi_products__count'), output_field=FloatField(), default=0),
    ).values_list('fact_total_pds', 'fact_total_tmz_count', 'fact_total_tmz_sum', 'fact_avg_price',
                  'total_pds', 'total_tmz_count', 'total_tmz_sum', 'avg_price')

    total_kpis = tuple(sum(x) for x in zip(*kpis))

    total_data = {
        'fact_total_pds': round(total_kpis[0]),  # Факт ПДС
        'fact_total_tmz_count': round(total_kpis[1]),  # Факт ТМЗ количество
        'fact_total_tmz_sum': round(total_kpis[2]),  # Факт ТМЗ количество
        'fact_avg_price': round(total_kpis[3]),  # Факт Средний чек

        'total_pds': round(total_kpis[4]),  # План ПДС
        'total_tmz_count': round(total_kpis[5]),  # План ТМЗ количество
        'total_tmz_sum': round(total_kpis[6]),  # План ТМЗ количество
        'avg_price': round(total_kpis[7]),  # План Средний чек

        'per_done_pds': round(total_kpis[4] / total_kpis[0] * 100),  # % ПДС
        'per_done_tmz_count': round(total_kpis[5] / total_kpis[1] * 100),  # % ТМЗ количество
        'per_done_tmz_sum': round(total_kpis[6] / total_kpis[2] * 100),  # % ТМЗ количество
        'per_done_avg_price': round(total_kpis[7] / total_kpis[3] * 100),  # % Средний чек
    }

    return total_data


def kpi_main_2lvl(month, stat_type):

    match stat_type:
        case 'pds':
            return kpi_pds_2lvl(month)
        case 'tmz':
            return kpi_tmz_2lvl(month)
        case 'sch':
            return kpi_sch_2lvl(month)
        case 'akb':
            return kpi_akb_2lvl(month)
        case 'svd':
            return kpi_svd_2lvl(month)


def kpi_pds_2lvl(month):
    managers = MyUser.objects.filter(is_active=True, status='manager', manager_profile__is_main=True)

    managers_data = []
    for manager in managers:
        kpis = DealerKPI.objects.filter(
            month__month=month, user__dealer_profile__managers=manager
        ).annotate(
            fact_total_pds=Sum("fact_pds", default=0),
            total_pds=Sum("pds", default=0),
        ).values_list('fact_total_pds', 'total_pds')

        total_kpis = tuple(sum(x) for x in zip(*kpis))
        if total_kpis:
            managers_data.append({
                'name': manager.name,
                'id': manager.id,
                'fact_total_pds': round(total_kpis[0]),
                'total_pds': round(total_kpis[1]),
                'per_done_pds': round(total_kpis[1] / total_kpis[0] * 100),
            })
    return managers_data


def kpi_tmz_2lvl(month):
    managers = MyUser.objects.filter(is_active=True, status='manager', manager_profile__is_main=True)

    managers_data = []
    for manager in managers:
        kpis = DealerKPI.objects.filter(
            month__month=month, user__dealer_profile__managers=manager
        ).annotate(
            fact_total_tmz_count=Sum('kpi_products__fact_count', default=0),
            fact_total_tmz_sum=Sum('kpi_products__fact_sum', default=0),
            total_tmz_count=Sum('kpi_products__count', default=0),
            total_tmz_sum=Sum('kpi_products__sum', default=0),
        ).values_list('fact_total_tmz_count', 'fact_total_tmz_sum', 'total_tmz_count', 'total_tmz_sum')

        total_kpis = tuple(sum(x) for x in zip(*kpis))
        if total_kpis:
            managers_data.append({
                'name': manager.name,
                'id': manager.id,
                'fact_total_tmz_count': round(total_kpis[0]),
                'fact_total_tmz_sum': round(total_kpis[1]),
                'total_tmz_count': round(total_kpis[2]),
                'total_tmz_sum': round(total_kpis[3]),
                'per_done_tmz_count': round(total_kpis[2] / total_kpis[0] * 100),
                'per_done_tmz_sum': round(total_kpis[3] / total_kpis[1] * 100),
            })
    return managers_data


def kpi_sch_2lvl(month):
    managers = MyUser.objects.filter(is_active=True, status='manager', manager_profile__is_main=True)

    managers_data = []
    for manager in managers:
        kpis = DealerKPI.objects.filter(
            month__month=month, user__dealer_profile__managers=manager
        ).annotate(
            fact_avg_price=Sum(F('kpi_products__fact_sum') / F('kpi_products__fact_count'), output_field=FloatField(),
                               default=0),
            avg_price=Sum(F('kpi_products__sum') / F('kpi_products__count'), output_field=FloatField(), default=0),
        ).values_list('fact_avg_price', 'avg_price')

        total_kpis = tuple(sum(x) for x in zip(*kpis))
        if total_kpis:
            managers_data.append({
                'name': manager.name,
                'id': manager.id,
                'fact_avg_price': round(total_kpis[0]),
                'avg_price': round(total_kpis[1]),
                'per_done_avg_price': round(total_kpis[1] / total_kpis[0] * 100),
            })
    return managers_data


def kpi_akb_2lvl(month):
    managers = MyUser.objects.filter(is_active=True, status='manager', manager_profile__is_main=True)

    managers_data = []
    for manager in managers:
        plan = manager.mngr_kpis.filter(month__month=month).first()

        users = MyUser.objects.filter(
            is_active=True, status='dealer', dealer_profile__managers=manager,
            dealer_profile__orders__created_at__month=month, dealer_profile__orders__is_active=True,
            dealer_profile__orders__status__in=['sent', 'success']
        )
        managers_data.append({
            'name': manager.name,
            'id': manager.id,
            'akb': plan.akb,
            'fact_akb': users.count(),
        })
    return managers_data


def kpi_svd_2lvl(month):
    managers = MyUser.objects.filter(is_active=True, status='manager', manager_profile__is_main=True)

    managers_data = []
    for manager in managers:
        before_data = manager.svds.filter(manager_kpi__month__month=month).values_list('product_id', 'count')
        before_data = [{item[0]: item[1]} if isinstance(item, tuple) else {item[0]: item[1]} for item in before_data]
        before_count = len(before_data)

        after_user_ids = manager.dealer_profiles.all().values_list('id', flat=True)
        after_data = OrderProduct.objects.filter(order__author_id__in=after_user_ids, order__is_active=True,
                                                 order__released_at__month=month,
                                                 order__status__in=['success', 'sent']).values_list('ab_product_id',
                                                                                                    'count')
        after_data = [{item[0]: item[1]} if isinstance(item, tuple) else {item[0]: item[1]} for item in after_data]
        after_count = len(after_data)

        old_count = 0
        share_old = 0
        sum_old = sum([value for dictionary in before_data for value in dictionary.values()])
        for b in before_data:
            p, c = b.items()
            after_ids = [key for dictionary in after_data for key in dictionary.keys()]
            if p not in after_ids:
                old_count += 1
                share_old += c / sum_old * 100

        new_count = 0
        share_new = 0
        sum_new = sum([value for dictionary in after_data for value in dictionary.values()])
        for b in after_data:
            p, c = b.items()
            before_ids = [key for dictionary in before_data for key in dictionary.keys()]
            if p not in before_ids:
                new_count += 1
                share_new += c / sum_new * 100

        managers_data.append({
            'before_count': before_count,
            'after_count': after_count,
            'old_count': old_count,
            'new_count': new_count,
            'share_old': share_old,
            'share_new': share_new
        })

    return managers_data



