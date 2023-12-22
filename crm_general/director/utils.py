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
            is_active=True, status__in=['sent', 'sent', 'success', 'wait'],
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
                    condition_data["condition_cats"].append(category_data)
                    total_count = sum(
                        order_products.count
                        for order in orders
                        for order_products in order.order_products.filter(category=condition_cat.category)
                    )
                    condition_data['done'] = total_count
                    condition_data['per'] = round(total_count * 100 / condition_cat.count)

            elif condition.status == 'product':
                condition_data["condition_prods"] = []
                condition_prods = condition.condition_prods.all()
                for condition_prod in condition_prods:
                    product_data = {
                        "count": condition_prod.count,
                        "product": condition_prod.product.id,
                        "product_title": condition_prod.product.title
                    }
                    condition_data["condition_prods"].append(product_data)

                    total_count = sum(
                        order_products.count
                        for order in orders
                        for order_products in order.order_products.filter(ab_product=condition_prod.product)
                    )
                    condition_data['done'] = total_count
                    condition_data['per'] = round(total_count * 100 / condition_prod.count)

            elif condition.status == 'money':
                condition_data["money"] = condition.money
                total_count = sum(orders.values_list('price', flat=True))
                condition_data['done'] = total_count
                condition_data['per'] = round(total_count * 100 / condition.money)

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

