import json

import requests

from account.models import DealerStatus
from general_service.models import Stock, City, PriceType
from product.models import AsiaProduct, Category, ProductCount, ProductPrice


def synchronization_back_to_1C():
    url = 'http://91.211.251.134/ab1c/hs/asoi/leftovers'
    username = 'Директор'
    password = '757520ля***'
    response = requests.get(url, auth=(username.encode('utf-8'), password.encode('utf-8')))
    data = json.loads(response.content)

    products = data.get('products')
    print(len(products))
    x = 0
    for p in products:
        x += 1

        category = Category.objects.filter(title__icontains=p['CategoryUID']).first()
        if category:
            product = AsiaProduct.objects.create(uid=p.get('NomenclatureUID'), title=p.get('NomenclatureName'),
                                                 category=category)
        else:
            product = AsiaProduct.objects.create(uid=p.get('NomenclatureUID'), title=p.get('NomenclatureName'))

        p_count_data = [{'stock': s, 'product': product} for s in Stock.objects.all()]
        ProductCount.objects.bulk_create([ProductCount(**i) for i in p_count_data])

        prod_price_data = []
        prices = PriceType.objects.all()
        for price in prices:
            dealer_statuses = DealerStatus.objects.all()

            for status in dealer_statuses:
                amount = 10000 * x
                prod_price_data.append(ProductPrice(price_type=price, product=product, price=amount,
                                                dealer_status=status))
        ProductPrice.objects.bulk_create(prod_price_data)
