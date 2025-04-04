from django.db.models import Sum

from order.db_request import query_debugger
from order.models import MainOrder
from product.models import AsiaProduct, ProductPrice


def check_product_count(products, stock):
    for k, v in products.items():
        prod_count = stock.counts.filter(product_id=k).first()
        if prod_count.count_crm < v:
            return False
    return True


def get_product_list(products):
    products_id = [k for k in products.keys()]
    product_list = AsiaProduct.objects.filter(id__in=products_id)
    return product_list


# def order_total_price(product_list, products, dealer):
#     price_type = dealer.price_type
#     if price_type:
#         prices = ProductPrice.objects.filter(product_id__in=product_list, price_type=price_type,
#                                              d_status=dealer.dealer_status).only("product_id", "price")
#     else:
#         prices = ProductPrice.objects.filter(product_id__in=product_list, city=dealer.price_city,
#                                              d_status=dealer.dealer_status).only("product_id", "price")
#     amount = 0
#     for price_data in prices:
#         product_id = price_data.product_id
#         price = price_data.price
#         amount += price * products[str(product_id)]
#
#     return amount


def order_total_price(product_list, product_counts, dealer):
    price_type = dealer.price_type
    dealer_status = dealer.dealer_status
    price_city = dealer.price_city
    amount = 0
    for product_obj in product_list:
        if price_type:
            prod_price_obj = (
                dealer.user.discount_prices.filter(
                    is_active=True,
                    product=product_obj,
                    price_type=price_type
                ).first()
                or
                product_obj.prices.filter(
                    price_type=price_type,
                    d_status=dealer_status
                ).first()
            )
        else:
            prod_price_obj = (
                dealer.user.discount_prices.filter(
                    is_active=True,
                    product=product_obj,
                    city=price_city
                ).first()
                or
                product_obj.prices.filter(
                    city=price_city,
                    d_status=dealer_status
                ).first()
            )

        prod_price = prod_price_obj.price
        sale_count = product_counts[str(product_obj.id)]
        amount += prod_price * sale_count

    return amount


def order_cost_price(product_list, products):
    amount = 0
    for p in product_list:
        cost_price = p.cost_prices.filter(is_active=True).values('price').first()
        amount += cost_price['price'] * products[str(p.id)]

    return amount


# def generate_order_products(product_list, products, dealer):
#     result_data = []
#     for p in product_list:
#         prod_price = p.prices.filter(price_type=dealer.price_type, d_status=dealer.dealer_status).first()
#
#         if not prod_price:
#             prod_price = p.prices.filter(city=dealer.price_city, d_status=dealer.dealer_status).first()
#
#         result_data.append({
#             "ab_product": p,
#             "count": products[str(p.id)],
#             "price": prod_price.price,
#         })
#
#     return result_data


def generate_order_products(product_list, product_counts, dealer):
    result_data = []
    price_type = dealer.price_type
    dealer_status = dealer.dealer_status
    price_city = dealer.price_city

    for product_obj in product_list:
        if price_type:
            prod_price_obj = (
                dealer.user.discount_prices.filter(
                    is_active=True,
                    product=product_obj,
                    price_type=price_type
                ).first()
                or
                product_obj.prices.filter(
                    price_type=price_type,
                    d_status=dealer_status
                ).first()
            )
        else:
            prod_price_obj = (
                dealer.user.discount_prices.filter(
                    is_active=True,
                    product=product_obj,
                    city=price_city
                ).first()
                or
                product_obj.prices.filter(
                    city=price_city,
                    d_status=dealer_status
                ).first()
            )

        prod_price = prod_price_obj.price
        discount_amount = prod_price_obj.old_price - prod_price
        cost_price = product_obj.cost_prices.filter(is_active=True).first().price
        sale_count = product_counts[str(product_obj.id)]
        result_data.append(
            {
                "ab_product": product_obj,
                "count": sale_count,
                "price": prod_price,
                "discount": discount_amount * sale_count,
                "unit_discount": discount_amount,
                "cost_price": cost_price
            }
        )
    return result_data


def validate_order_before_sending(main_order: MainOrder, products: dict[str:int]) -> bool:
    main_order_products = main_order.products.all()
    for product in main_order_products:
        if str(product.ab_product.id) in products:
            if products[str(product.ab_product.id)] > product.count:
                return False

    return True


def update_main_order_status(main_order: MainOrder):
    """
    Update main order status after shipment (sent)
    """
    main_order_products_data = main_order.products.aggregate(Sum('count'))
    if main_order_products_data['count__sum'] is None:
        main_order.status = 'sent'
    elif main_order_products_data['count__sum'] > 0:
        main_order.status = 'partial'

    main_order.save()
    return main_order
