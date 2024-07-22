import datetime

from django.db.models import Sum, Case, F, When, Value, DecimalField, IntegerField, ExpressionWrapper, FloatField
from django.utils import timezone

from order.models import OrderProduct, MyOrder


def purchase_analysis(request):
    order_statuses = {
        "all": None,
        "active": ['wait', 'created', 'paid'],
        "done": ['sent', 'success'],
        "cancel": ['rejected']
    }
    start = request.data.get('start')
    end = request.data.get('end')
    kwargs = {}
    start_date = timezone.make_aware(datetime.datetime.strptime(start, "%d-%m-%Y"))
    end_date = timezone.make_aware(datetime.datetime.strptime(end, "%d-%m-%Y"))
    end_date = end_date + datetime.timedelta(days=1)
    o_status = order_statuses.get(request.data.get('status'))
    if o_status:
        kwargs['status__in'] = o_status
    kwargs['created_at__gte'] = start_date
    kwargs['created_at__lte'] = end_date

    orders = request.user.dealer_profile.orders.filter(
        is_active=True, **kwargs
    ).annotate(
        total_price=Sum('price', default=0, output_field=IntegerField()),
        true_price=Sum(
            Case(
                When(order_products__discount=0, then=F("order_products__total_price")),
                default=0,
                output_field=IntegerField()
            )
        ),
        discount_price=Sum(
            Case(
                When(order_products__discount__gt=0, then=F("order_products__total_price")),
                default=0,
                output_field=IntegerField()
            )
        ),
        eco_price=Sum(
            Case(
                When(order_products__discount__gte=0, then=F("order_products__discount")),
                default=0,
                output_field=IntegerField()
            )
        ),
    )
    orders2 = request.user.dealer_profile.orders.select_related(
        'stock').prefetch_related('order_products__category').filter(
        is_active=True, **kwargs
    )
    stock_list = orders2.values_list('stock__title', flat=True).distinct()
    stock_info = {}
    for stock in stock_list:
        if stock:
            stock_info[stock] = sum(orders2.filter(stock__title=stock).values_list('price', flat=True))

    categories_list = orders2.values_list('order_products__ab_product__category__title', flat=True).distinct()
    cat_info = {}
    for cat in categories_list:
        if cat:
            cat_info[cat] = sum(orders2.filter(
                order_products__ab_product__category__title=cat
            ).annotate(
                total_price=Sum(ExpressionWrapper(
                    F('order_products__price') * F('order_products__count'),
                    output_field=FloatField()
                ), default=0)
            ).values_list('total_price', flat=True))

    result_data = {
        "total_price": sum(orders.values_list('total_price', flat=True)),
        "discount_price": sum(orders.values_list('discount_price', flat=True)),
        "eco_price": sum(orders.values_list('eco_price', flat=True)),
        "true_price": sum(orders.values_list('true_price', flat=True)),
        "categories_list": [{k: v} for k, v in cat_info.items()],
        "cities_list": [{k: v} for k, v in stock_info.items()]
    }
    return result_data




