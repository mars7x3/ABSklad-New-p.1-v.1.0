from product.models import AsiaProduct


def check_product_count(products, stock):
    for p in products:
        prod_count = stock.counts.filter(product_id=p.key()).first()
        if prod_count.count < p.value():
            return False
    return True


def get_product_list(products):
    products_id = [v.key() for v in products]
    product_list = AsiaProduct.objects.filter(id__in=products_id).prefetch_related('cost_prices', 'prices')
    return product_list


def order_total_price(product_list, products, dealer):
    amount = 0
    for p in product_list:
        prod_price = p.prices.filter(city=dealer.price_city, d_status=dealer.dealer_status).first()
        amount += prod_price.price * int(products.get(p.id))

    return amount


def order_cost_price(product_list, products):
    amount = 0
    for p in product_list:
        cost_price = p.cost_prices.filter(is_active=True).first()
        amount += cost_price.price * int(products.get(p.id))

    return amount


def generate_order_products(product_list, products, dealer):
    result_data = []
    for p in product_list:
        prod_price = p.prices.filter(city=dealer.price_city, d_status=dealer.dealer_status).first()
        total_price = prod_price.price * int(products.get(p.id))
        discount = abs(prod_price.old_orice - prod_price.price)

        result_data.append({
            "ab_product": p.id,
            "category": p.category,
            "title": p.title,
            "count": products.get(p.id),
            "price": prod_price.price,
            "total_price": total_price,
            "discount": discount,
            "image": p.image
        })

    return result_data
