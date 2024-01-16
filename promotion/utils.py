import datetime

from dateutil.relativedelta import relativedelta
from django.db.models import Sum
from django.utils import timezone

from order.models import MyOrder
from promotion.models import DealerKPIProduct


def get_motivation_data(dealer):
    motivations_data = []
    motivations = dealer.motivations.filter(is_active=True)

    for motivation in motivations:
        motivation_data = {
            "title": motivation.title,
            "start_date": motivation.start_date,
            "end_date": motivation.end_date,
            "is_active": motivation.is_active,
            "conditions": []
        }

        conditions = motivation.conditions.all()
        orders = dealer.orders.filter(
            is_active=True, status__in=['sent', 'paid', 'success', 'wait'],
            paid_at__gte=motivation.start_date)

        for condition in conditions:
            condition_data = {
                "status": condition.status,
                "presents": []
            }

            if condition.status == 'category':
                condition_data["condition_cats"] = []
                condition_cats = condition.condition_cats.all()
                for condition_cat in condition_cats:
                    category_data = {
                        "count": condition_cat.count,
                        "category": condition_cat.category.id,
                        "category_title": condition_cat.category.title
                    }
                    total_count = sum(
                        order_products.count
                        for order in orders
                        for order_products in order.order_products.filter(category=condition_cat.category)
                    )
                    category_data['per'] = round(total_count * 100 / condition_cat.count)
                    category_data['done'] = float(total_count)

                    condition_data["condition_cats"].append(category_data)

            elif condition.status == 'product':
                condition_data["condition_prods"] = []
                condition_prods = condition.condition_prods.all()
                for condition_prod in condition_prods:
                    product_data = {
                        "count": condition_prod.count,
                        "product": condition_prod.product.id,
                        "product_title": condition_prod.product.title
                    }

                    total_count = sum(
                        order_products.count
                        for order in orders
                        for order_products in order.order_products.filter(ab_product=condition_prod.product)
                    )
                    product_data['per'] = round(total_count * 100 / condition_prod.count)
                    product_data['done'] = float(total_count)

                    condition_data["condition_prods"].append(product_data)

            elif condition.status == 'money':
                condition_data["money"] = condition.money
                total_count = sum(orders.values_list('price', flat=True))
                condition_data['per'] = round(total_count * 100 / condition.money)
                condition_data['done'] = float(total_count)

            presents = condition.presents.all()
            for p in presents:
                present_data = {
                    "status": p.status,
                    "money": p.money,
                    "text": p.text
                }

                condition_data["presents"].append(present_data)

            motivation_data["conditions"].append(condition_data)

        motivations_data.append(motivation_data)

    return motivations_data


def get_kpi_info(user):
    kpi = user.kpis.filter(month__month=datetime.datetime.now().month).first()
    tmz = sum(kpi.kpi_products.all().values_list('count', flat=True))
    fact_tmz = sum(kpi.kpi_products.all().values_list('fact_count', flat=True))
    return {'pds': kpi.pds, 'tmz': tmz, 'fact_pds': kpi.fact_pds, 'fact_tmz': fact_tmz}


def get_kpi_products(user):
    kpi = user.kpis.filter(month__month=datetime.datetime.now().month).first()
    prods = kpi.kpi_products.all().select_related('product')
    prods_data = []
    for p in prods:
        prods_data.append(
            {
                'title': p.product.title,
                'id': p.product.id,
                'count': p.count,
                'fact_count': p.fact_count
            }
        )
    return prods_data


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
