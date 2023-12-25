from decimal import Decimal
from pprint import pprint

from order.models import OrderProduct
from django.db.models import OuterRef, Subquery

from product.models import ProductPrice


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


def get_motivation_margin(motivation):
    amount = 0
    for condition in motivation.conditions.all():
        match condition.status:
            case 'category':
                total_amount = 0
                for cat in condition.condition_cats.all():
                    total_amount += sum(cat.category.order_products.filter(
                        order__is_active=True, order__status__in=['paid', 'sent', 'wait', 'success'],
                        order__paid_at__gte=motivation.start_date, order__paid_at__lte=motivation.end_date,
                        order__author__in=motivation.dealers.all()
                    ).values_list('total_price', flat=True))
                amount += total_amount

            case 'product':
                total_amount = 0
                for prod in condition.condition_prods.all():
                    total_amount += sum(prod.product.order_products.filter(
                        order__is_active=True, order__status__in=['paid', 'sent', 'wait', 'success'],
                        order__paid_at__gte=motivation.start_date, order__paid_at__lte=motivation.end_date,
                        order__author__in=motivation.dealers.all()
                    ).values_list('total_price', flat=True))
                amount += total_amount

            case 'money':
                total_amount = sum(MyOrder.objects.filter(
                    is_active=True, status__in=['paid', 'sent', 'wait', 'success'],
                    paid_at__gte=motivation.start_date, paid_at__lte=motivation.end_date,
                    author__in=motivation.dealers.all()
                ).values_list('price', flat=True))
                amount += total_amount

    return amount


from django.db.models import Q, F, Case, When, Sum, Value, ExpressionWrapper, DecimalField, FloatField
from django.db.models.functions import Round
from django.utils.timezone import now

from order.models import MyOrder
from promotion.models import Motivation



def test(motivation: Motivation, page: int = 1, page_size: int = 10):
    dealers_count = motivation.dealers.count()  # 100
    pages_count = dealers_count // page_size or 1
    limit = page_size
    offset = limit * page if page > 1 else 0

    total_days = (motivation.end_date - motivation.start_date).days
    today = now()
    if motivation.start_date < today < motivation.end_date:
        passed_days = (today - motivation.start_date).days
    elif motivation.start_date > today < motivation.end_date:
        passed_days = 0
    else:
        passed_days = total_days

    print("Start Date: ", str(motivation.start_date), " End Date: ", str(motivation.end_date),
          " Total Days: ", total_days)
    print("Today: ", str(today.date()), " Passed Days: ", passed_days)

    page_dealers = motivation.dealers.all()[offset:offset + limit]
    print("Pages count: ", pages_count, "Page: ", page,  "Items per page: ", page_dealers.count())

    data = (
        MyOrder.objects.filter(
            author__in=page_dealers,
            paid_at__date__gte=motivation.start_date,
            paid_at__date__lte=motivation.end_date
        ).values("name")
        .annotate(
            margin=Sum("price"),
            consumption=Sum("cost_price"),
            gift_amount=Sum("author__motivations__conditions__presents__money"),
            spent_price=Sum("order_products__total_price"),
            target=Sum("author__motivations__conditions__money")
        )
        .annotate(
            process=Round(
                ExpressionWrapper(F("margin") * Value(100) / F("target"), output_field=FloatField()),
                precision=2
            ),
            city=F("author__city__title")
        )
        .annotate(
            revenue=Case(
                When(
                    process=100,
                    then=ExpressionWrapper(
                        F("margin") - F("consumption") - F("gift_amount"),
                        output_field=DecimalField()
                    )
                ),
                default=Value(Decimal("0.0"))
            ),
            probability=Round(
                ExpressionWrapper(
                    ((F("spent_price") / Value(passed_days)) * Value(total_days)) / F("target") * Value(100),
                    output_field=FloatField()
                ),
                precision=2
            )
        )
    )
    pprint(list(data))


def get_motivation_dealers_stat(motivation: Motivation):

    total_days = (motivation.end_date - motivation.start_date).days
    today = now()
    if motivation.start_date < today < motivation.end_date:
        passed_days = (today - motivation.start_date).days
    elif motivation.start_date > today < motivation.end_date:
        passed_days = 0
    else:
        passed_days = total_days

    print("Start Date: ", str(motivation.start_date), " End Date: ", str(motivation.end_date),
          " Total Days: ", total_days)
    print("Today: ", str(today.date()), " Passed Days: ", passed_days)

    page_dealers = motivation.dealers.all()

    print('------------------------------------------------ Money ')
    money_condition = motivation.conditions.filter(status="money").first()
    if money_condition:
        money_target = money_condition.money
        gift_amount = money_condition.presents.aggregate(gift_amount=Sum("money"))["gift_amount"]

        money_data = (
            MyOrder.objects.filter(
                author__in=page_dealers,
                paid_at__date__gte=motivation.start_date,
                paid_at__date__lte=motivation.end_date
            ).values("author_id", "name")
            .annotate(
                city=F("author__city__title"),
                margin=Sum("price"),
                consumption=Sum("cost_price")
            )
            .annotate(
                process=Round(
                    ExpressionWrapper(F("margin") * Value(100) / Value(money_target), output_field=FloatField()),
                    precision=2
                ),
                probability=Round(
                    ExpressionWrapper(
                        ((F("margin") / Value(passed_days)) * Value(total_days)) / Value(money_target) * Value(100),
                        output_field=FloatField()
                    ),
                    precision=2
                )
            )
            .annotate(
                revenue=Case(
                    When(
                        process=100,
                        then=ExpressionWrapper(
                            F("margin") - F("consumption") - Value(gift_amount),
                            output_field=DecimalField()
                        )
                    ),
                    default=Value(Decimal("0.0"))
                )
            )
        )
        print("Money Target: ", money_target)
        print("Gift amount: ", gift_amount)
        print("Money data: ")
        pprint(list(money_data))

    print('------------------------------------------------ Category ')
    main_category_condition = motivation.conditions.filter(status="category").first()
    if main_category_condition:
        gift_amount = main_category_condition.presents.aggregate(gift_amount=Sum("money"))["gift_amount"]
        for category_condition in main_category_condition.condition_cats.all():
            category_data = (
                OrderProduct.objects.filter(
                    order__author__in=page_dealers,
                    order__paid_at__date__gte=motivation.start_date,
                    order__paid_at__date__lte=motivation.end_date,
                    category=category_condition.category
                )
                .values(
                    "category_id",
                    author_id=F("order__author_id"),
                    name=F("order__name"),
                    city=F("order__author__city__title")
                )
                .annotate(sales_count=Sum("count"))
                .annotate(
                    margin=Sum("total_price"),
                    consumption=Sum("cost_price"),
                    process=Round(
                        ExpressionWrapper(
                            F("sales_count") * Value(100) / Value(category_condition.count),
                            output_field=FloatField()
                        ),
                        precision=2
                    ),
                    probability=Round(
                        ExpressionWrapper(
                            (
                                (F("sales_count") / Value(passed_days)) * Value(total_days)
                            ) / Value(category_condition.count) * Value(100),
                            output_field=FloatField()
                        ),
                        precision=2
                    )
                )
                .annotate(
                    # выручка
                    revenue=Case(
                        When(
                            process=100,
                            then=ExpressionWrapper(
                                F("margin") - F("consumption") - Value(gift_amount),
                                output_field=DecimalField()
                            )
                        ),
                        default=Value(Decimal("0.0"))
                    )
                )
            )

            print("Category: ", category_condition.category.title)
            print("Category Target Count: ", category_condition.count)
            print("Gift amount: ", gift_amount)
            print("Category: data: ")
            pprint(list(category_data))

    print('------------------------------------------------ Product ')
    main_product_condition = motivation.conditions.filter(status="product").first()
    if main_product_condition:
        gift_amount = main_product_condition.presents.aggregate(gift_amount=Sum("money"))["gift_amount"]

        for product_condition in main_product_condition.condition_prods.all():
            product_data = (
                OrderProduct.objects.filter(
                    order__author__in=page_dealers,
                    order__paid_at__date__gte=motivation.start_date,
                    order__paid_at__date__lte=motivation.end_date,
                    ab_product=product_condition.product
                )
                .values(
                    product_id=F("ab_product_id"),
                    author_id=F("order__author_id"),
                    name=F("order__name"),
                    city=F("order__author__city__title")
                )
                .annotate(sales_count=Sum("count"))
                .annotate(
                    margin=Sum("total_price"),
                    consumption=Sum("cost_price"),
                    process=Round(
                        ExpressionWrapper(
                            F("sales_count") * Value(100) / Value(product_condition.count),
                            output_field=FloatField()
                        ),
                        precision=2
                    ),
                    probability=Round(
                        ExpressionWrapper(
                            (
                                (F("sales_count") / Value(passed_days)) * Value(total_days)
                            ) / Value(product_condition.count) * Value(100),
                            output_field=FloatField()
                        ),
                        precision=2
                    )
                )
                .annotate(
                    # выручка
                    revenue=Case(
                        When(
                            process=100,
                            then=ExpressionWrapper(
                                F("margin") - F("consumption") - Value(gift_amount),
                                output_field=DecimalField()
                            )
                        ),
                        default=Value(Decimal("0.0"))
                    )
                )
            )
            print("Product: ", product_condition.product.title)
            print("Product Target Count: ", product_condition.count)
            print("Gift amount: ", gift_amount)
            print("Product: data: ")
            pprint(list(product_data))


# def get_motivation_total_stats(motivations):
#
#     money_data = (
#         MyOrder.objects.filter(
#             author__in=page_dealers,
#             paid_at__date__gte=motivation.start_date,
#             paid_at__date__lte=motivation.end_date
#         ).values("author_id", "name")
#         .annotate(
#             city=F("author__city__title"),
#             margin=Sum("price"),
#             consumption=Sum("cost_price")
#         )
#         .annotate(
#             process=Round(
#                 ExpressionWrapper(F("margin") * Value(100) / Value(money_target), output_field=FloatField()),
#                 precision=2
#             ),
#             probability=Round(
#                 ExpressionWrapper(
#                     ((F("margin") / Value(passed_days)) * Value(total_days)) / Value(money_target) * Value(100),
#                     output_field=FloatField()
#                 ),
#                 precision=2
#             )
#         )
#         .annotate(
#             revenue=Case(
#                 When(
#                     process=100,
#                     then=ExpressionWrapper(
#                         F("margin") - F("consumption") - Value(gift_amount),
#                         output_field=DecimalField()
#                     )
#                 ),
#                 default=Value(Decimal("0.0"))
#             )
#         )
#     )


