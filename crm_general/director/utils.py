from decimal import Decimal

from django.db.models import Q, OuterRef, Subquery

from general_service.models import Stock
from product.models import ProductPrice, ProductCount
from order.db_request import query_debugger


def prod_total_amount_crm(stock):
    # stock.counts.annotate()
    # stocks = Stock.objects.all()

    from django.db.models import F, ExpressionWrapper, Sum, IntegerField
    # price_subquery = ProductPrice.objects.filter(city=OuterRef('city'), product=OuterRef('counts__product'),
    #                                              d_status__discount=0).values('price')[:1]

    return stock.counts.aggregate(
        total_sum=Sum(
            F('count_crm') * Subquery(
                ProductPrice.objects.filter(
                    city=OuterRef('stock__city'),
                    product_id=OuterRef('product_id'),
                    d_status__discount=0
                ).values('price')[:1]
            ), output_field=IntegerField()
        )
    )["total_sum"]

    # stocks_with_total_cost = Stock.objects.annotate(
    #     total_cost=Sum(ExpressionWrapper(F('counts__count_crm') * Subquery(price_subquery), output_field=IntegerField()))
    # )
    # return str(stocks_with_total_cost)
    # for s in stocks_with_total_cost:
    #     print(s.city.title)
    #     print(s.total_cost)

    # for s in stocks:
    #     amount = 0
    #     for p in s.counts.all():
    #         price = ProductPrice.objects.filter(product=p.product, city=s.city, d_status__discount=0).first()
    #         count = p.count_crm
    #         amount += price.price * count
    #
    #     print(s.city.title)
    #     print(amount)


def get_motivation_done(dealer):
    response_data = []
    for m in dealer.motivations.filter(is_active=True):
        m_data = {"title": m.title}
        for c in m.conditions.all():
            m_data['status'] = c.status
            if c.status == 'category':
                for c_c in c.condition_cats.all():
                    total_count = 0
                    orders = dealer.orders.filter(
                        is_active=True, status__in=['Отправлено', 'Оплачено', 'Успешно', 'Ожидание'],
                        paid_at__gte=m.start_date)
                    for o in orders:
                        total_count += sum(o.order_products.filter(category=c_c.category
                                                                   ).values_list('count', flat=True))
                    per = total_count * 100 / c_c.count
                    m_data['per'] = round(per)
                    m_data['total_count'] = c_c.count
                    m_data['done_count'] = total_count
                    m_data['category_title'] = c_c.category.title

            elif c.status == 'product':
                for c_p in c.condition_prods.all():
                    total_count = 0
                    orders = dealer.orders.filter(
                        is_active=True, status__in=['Отправлено', 'Оплачено', 'Успешно', 'Ожидание'],
                        paid_at__gte=m.start_date)
                    for o in orders:
                        total_count += sum(o.order_products.filter(ab_product=c_p.product
                                                                   ).values_list('count', flat=True))
                    per = total_count * 100 / c_p.count
                    m_data['per'] = round(per)
                    m_data['total_count'] = c_p.count
                    m_data['done_count'] = total_count
                    m_data['product_title'] = c_p.product.title

            elif c.status == 'money':

                total_price = sum(dealer.orders.filter(
                    is_active=True, status__in=['Отправлено', 'Оплачено', 'Успешно', 'Ожидание'],
                    paid_at__gte=m.start_date).values_list('price', flat=True))
                per = total_price * 100 / c.money
                m_data['per'] = round(per)
                m_data['total_amount'] = c.money
                m_data['done_amount'] = total_price
            m_data['presents'] = [
                {
                    "status": p.status,
                    "product": p.product,
                    "money": p.money,
                    "text": p.text
                 }
                for p in c.presents.all()
            ]
            response_data.append(m_data)
    return response_data
