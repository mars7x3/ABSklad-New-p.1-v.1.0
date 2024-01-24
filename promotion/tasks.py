import datetime

from absklad_commerce.celery import app
from promotion.utils import calculate_discount
from general_service.models import PriceType, City
from product.models import ProductPrice, AsiaProduct
from promotion.models import Discount, DiscountPrice


@app.task
def activate_discount():
    crn_date = datetime.date.today()
    discounts = Discount.objects.filter(start_date=crn_date)
    price_types = PriceType.objects.all()
    cities = City.objects.all()

    discounts_to_activate = []
    for discount in discounts:
        print(f'---Activating discount {discount.id} | Discount status -> {discount.status}')
        discount.is_active = True
        discounts_to_activate.append(discount)

        products = discount.products.all()
        dealers = discount.dealer_profiles.all()
        discount_amount = discount.amount
        discount_prices_to_create = []
        products_to_update = []

        for product in products:
            product.is_discount = True
            products_to_update.append(product)

            for dealer in dealers:
                if dealer.price_type:
                    product_price = ProductPrice.objects.filter(product=product,
                                                                d_status__discount=0,
                                                                price_type=dealer.price_type).first()
                else:
                    product_price = ProductPrice.objects.filter(product=product,
                                                                d_status__discount=0,
                                                                city=dealer.village.city).first()
                product_base_price = product_price.price

                if discount.status == 'Per':
                    dealer_discount_amount = int(dealer.dealer_status.discount)
                    total_discount_percent = discount_amount + dealer_discount_amount
                    final_price = calculate_discount(int(product_base_price), total_discount_percent)
                elif discount.status == 'Sum':
                    amount_without_abc = product_base_price - discount_amount
                    final_price = calculate_discount(int(amount_without_abc), int(dealer.dealer_status.discount))

                    for price_type in price_types:
                        discount_prices_to_create.append(
                            DiscountPrice(
                                user=dealer.user,
                                discount=discount,
                                product=product,
                                city=None,
                                price_type=price_type,
                                price=final_price,
                                old_price=product_base_price,
                                is_active=True
                            )
                        )

                    for city in cities:
                        discount_prices_to_create.append(
                            DiscountPrice(
                                user=dealer.user,
                                discount=discount,
                                product=product,
                                city=city,
                                price_type=None,
                                price=final_price,
                                old_price=product_base_price,
                                is_active=True
                            )
                        )

        DiscountPrice.objects.bulk_create(discount_prices_to_create)
        AsiaProduct.objects.bulk_update(products_to_update, fields=['is_discount'])
    Discount.objects.bulk_update(discounts_to_activate, fields=['is_active'])


@app.task
def deactivate_discount():
    crn_date = datetime.date.today()
    discounts = Discount.objects.filter(end_date=crn_date)

    discounts_to_deactivate = []
    for discount in discounts:
        print(f'---Deactivating discount {discount.id} | Discount status -> {discount.status}')
        discount.is_active = False
        discounts_to_deactivate.append(discount)
        discount_prices_to_deactivate = []
        discount_prices = discount.discount_prices.all()

        products = discount.products.all()
        products_to_update = []
        for product in products:
            product.is_discount = False
            products_to_update.append(product)

        for discount_price in discount_prices:
            discount_price.is_active = False
            discount_prices_to_deactivate.append(discount_price)

        AsiaProduct.objects.bulk_update(products_to_update, fields=['is_discount'])
        DiscountPrice.objects.bulk_update(discount_prices_to_deactivate, fields=['is_active'])
    Discount.objects.bulk_update(discounts_to_deactivate, fields=['is_active'])


