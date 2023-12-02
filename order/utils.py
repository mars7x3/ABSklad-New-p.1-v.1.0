from order.db_request import query_debugger
from product.models import AsiaProduct, ProductPrice


@query_debugger
def check_product_count(products, stock):
    for k, v in products.items():
        prod_count = stock.counts.filter(product_id=k).first()
        if prod_count.count_crm < v:
            return False
    return True


@query_debugger
def get_product_list(products):
    products_id = [k for k in products.keys()]
    product_list = AsiaProduct.objects.filter(id__in=products_id)
    return product_list


@query_debugger
def order_total_price(product_list, products, dealer):
    amount = 0
    prices = ProductPrice.objects.filter(product_id__in=product_list, city_id=1,
                                         d_status_id=1).only("product_id", "price")
    for price_data in prices:
        product_id = price_data.product_id
        price = price_data.price
        amount += price * products[str(product_id)]

    return amount


@query_debugger
def order_cost_price(product_list, products):
    amount = 0
    for p in product_list:
        cost_price = p.cost_prices.filter(is_active=True).first()
        amount += cost_price.price * products[str(p.id)]

    return amount


@query_debugger
def generate_order_products(product_list, products, dealer):
    result_data = []
    for p in product_list:
        prod_price = p.prices.filter(city=dealer.price_city, d_status=dealer.dealer_status).first()
        total_price = prod_price.price * products[str(p.id)]
        discount = abs(prod_price.old_price - prod_price.price)

        result_data.append({
            "ab_product": p,
            "category": p.category,
            "title": p.title,
            "count": products[str(p.id)],
            "price": prod_price.price,
            "total_price": total_price,
            "discount": discount,
            "image": p.images.first().image
        })

    return result_data
