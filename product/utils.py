
def get_product_price(user, product):
    dealer = user.dealer_profile
    if product.is_discount:
        discount_price_type = user.discount_prices.select_related('discount').filter(
            is_active=True,
            product=product,
            price_type=dealer.price_type).first()
        if discount_price_type:
            return {
                'price': discount_price_type.price,
                'old_price': discount_price_type.old_price,
                'discount': discount_price_type.discount.amount,
                'discount_status': discount_price_type.discount.status
            }

        discount_price_city = user.discount_prices.select_related('discount').filter(
            is_active=True,
            product=product,
            city=dealer.price_city).first()
        if discount_price_city:
            return {
                'price': discount_price_city.price,
                'old_price': discount_price_city.old_price,
                'discount': discount_price_city.discount.amount,
                'discount_status': discount_price_city.discount.status
            }

    if dealer.price_type:
        product_price = product.prices.filter(price_type=dealer.price_type, d_status=dealer.dealer_status).first()

    else:
        product_price = product.prices.filter(city=dealer.price_city, d_status=dealer.dealer_status).first()

    if product_price:
        return {
            'price': product_price.price,
            'old_price': product_price.old_price,
            'discount': dealer.dealer_status.discount,
            'discount_status': "Per"
        }
    else:
        return {
            'price': 0.0,
            'old_price': 0.0,
            'discount': 0.0,
            'discount_status': "Per"
        }
