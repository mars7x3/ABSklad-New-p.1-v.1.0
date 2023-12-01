import datetime


from django.utils import timezone

from order.models import OrderProduct, MyOrder


def purchase_analysis(request):
    order_statuses = {
        "all": None,
        "active": ['Ожидание', 'Новый', 'Оплачено'],
        "done": ['Отправлено', 'Успешно'],
        "cancel": ['Отказано']
    }
    start = request.data.get('start')
    end = request.data.get('end')
    o_status = order_statuses.get((request.data.get('status')))
    start_date = timezone.make_aware(datetime.datetime.strptime(start, "%d-%m-%Y"))
    end_date = timezone.make_aware(datetime.datetime.strptime(end, "%d-%m-%Y"))
    orders = (request.user.dealer_profile.orders.filter(created_at__gte=start_date, created_at__lte=end_date,
                                                        is_active=True)
              .select_related('stock__city').prefetch_related('order_products__category'))
    if o_status:
        orders = orders.filter(status__in=o_status)

    total_price = sum(orders.values_list('price', flat=True))
    eco_price = sum(orders.values_list('order__products__price', flat=True))
    true_price = sum(orders.filter(order__products__discount=0)
                     .values_list('order_products__total_price', flat=True))
    discount_price = total_price - true_price

    cities_list = orders.values_list('stock__city__title', flat=True).distinct()
    city_info = {}
    for city in cities_list:
        city_info[city] = sum(orders.filter(stock__city__title=city).values_list('price', flat=True))

    categories_list = orders.values_list('order__products__category__title', flat=True).distinct()
    cat_info = {}
    for cat in categories_list:
        cat_info[cat] = sum(orders.filter(order__products__category__title=cat)
                            .values_list('order__products__total_price', flat=True))

    result_data = {
        "total_price": total_price,
        "discount_price": discount_price,
        "eco_price": eco_price,
        "true_price": true_price,
        "categories_list": [{k: v} for k, v in cat_info.items()],
        "cities_list": [{k: v} for k, v in city_info.items()]
    }
    return result_data




