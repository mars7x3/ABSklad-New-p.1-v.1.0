from django.db.models import Q, OuterRef, Subquery

from general_service.models import Stock
from product.models import ProductPrice, ProductCount


def prod_total_amount_crm(stock):
    stock.counts.annotate()
    stocks = Stock.objects.all()

    from django.db.models import F, ExpressionWrapper, Sum, IntegerField
    price_subquery = ProductPrice.objects.filter(city=OuterRef('city'), product=OuterRef('counts__product'),
                                                 d_status__discount=0).values('price')[:1]

    stocks_with_total_cost = stocks.annotate(
        total_cost=Sum(ExpressionWrapper(F('counts__count_crm') * Subquery(price_subquery), output_field=IntegerField()))
    )
    for s in stocks_with_total_cost:
        print(s.city.title)
        print(s.total_cost)

    # for s in stocks:
    #     amount = 0
    #     for p in s.counts.all():
    #         price = ProductPrice.objects.filter(product=p.product, city=s.city, d_status__discount=0).first()
    #         count = p.count_crm
    #         amount += price.price * count
    #
    #     print(s.city.title)
    #     print(amount)



