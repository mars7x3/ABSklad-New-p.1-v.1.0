import logging

from django.utils import timezone

from absklad_commerce.celery import app
from account.utils import send_push_notification
from crm_general.utils import create_notifications_for_users
from promotion.utils import calculate_discount
from general_service.models import PriceType, City
from product.models import ProductPrice, AsiaProduct
from promotion.models import Discount, DiscountPrice, Story


@app.task
def activate_discount():
    naive_time = timezone.localtime().now()
    crn_date = timezone.make_aware(naive_time)
    discounts = Discount.objects.filter(start_date=crn_date, is_active=False)
    price_types = PriceType.objects.all()
    cities = City.objects.all()

    discounts_to_activate = []
    discount_prices_to_create = []
    products_to_update = []
    notifications = []

    for discount in discounts:
        print(f'---Activating discount {discount.id} | Discount status -> {discount.status}')
        discount.is_active = True
        discounts_to_activate.append(discount)

        products = discount.products.all()
        dealers = discount.dealer_profiles.all()
        discount_amount = discount.amount

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
                if dealer.dealer_status:
                    dealer_discount_amount = int(dealer.dealer_status.discount)
                else:
                    dealer_discount_amount = 0

                if discount.status == 'Per':
                    total_discount_percent = discount_amount + dealer_discount_amount
                    final_price = calculate_discount(int(product_base_price), total_discount_percent)
                elif discount.status == 'Sum':
                    abc_price = calculate_discount(product_base_price, dealer_discount_amount)
                    final_price = abc_price - discount_amount
                else:
                    return 'Discount type incorrect!!!'

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

        notifications.append(
            {
                "tokens": list(discount.dealer_profiles.all().values_list('user__fb_tokens__token', flat=True)),
                "title": f"Акция",
                'text': str(discount.title),
                'link_id': discount.id,
                "status": "action"
            }
        )

    DiscountPrice.objects.bulk_create(discount_prices_to_create)
    AsiaProduct.objects.bulk_update(products_to_update, fields=['is_discount'])
    Discount.objects.bulk_update(discounts_to_activate, fields=['is_active'])

    # important: send notification after discount update, otherwise notification will be false
    for notif_kwargs in notifications:
        try:
            create_notifications_for_users(crm_status='action', link_id=notif_kwargs["link_id"])
            send_push_notification(**notif_kwargs)   # TODO: delay() add here
        except Exception as exc:
            logging.error(exc)



@app.task
def deactivate_discount():
    naive_time = timezone.localtime().now()
    crn_date = timezone.make_aware(naive_time)
    discounts = Discount.objects.filter(end_date__lt=crn_date, is_active=True)

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


@app.task
def story_setter():
    naive_time = timezone.localtime().now()
    now = timezone.make_aware(naive_time)
    activate_stories = Story.objects.filter(is_active=False, start_date__lte=now, end_date__gte=now)
    deactivate_stories = Story.objects.filter(is_active=True, start_date__lte=now, end_date__lte=now)
    stories_to_update = []
    for story in activate_stories:
        story.is_active = True
        stories_to_update.append(story)

    for story in deactivate_stories:
        story.is_active = False
        stories_to_update.append(story)
    Story.objects.bulk_update(stories_to_update, fields=['is_active'])
