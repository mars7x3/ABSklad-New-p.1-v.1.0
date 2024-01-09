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
        print(x)
        product = AsiaProduct.objects.filter(uid=p.get('NomenclatureUID')).first()

        if not product:
            category = Category.objects.filter(uid=p['CategoryUID']).first()
            if category:
                product = AsiaProduct.objects.create(uid=p.get('NomenclatureUID'), title=p.get('NomenclatureName'),
                                                     category=category)
            else:
                continue

        p_count_data = [ProductCount(stock=s, product=product) for s in Stock.objects.all()]
        product.counts.all().delete()
        ProductCount.objects.bulk_create(p_count_data)

        prod_count_data = []
        for s in p.get('WarehousesCount'):
            stock = Stock.objects.filter(uid=s.get('WarehouseUID')).first()
            if stock:
                count = ProductCount.objects.filter(stock=stock, product=product).first()
                count.count_1c = s.get('NomenclatureAmount')
                count.count_crm = s.get('NomenclatureAmount')
                count.count_norm = 20
                prod_count_data.append(count)
        ProductCount.objects.bulk_update(prod_count_data, ['count'])

        price_types = []
        for pri in PriceType.objects.all():
            for sta in DealerStatus.objects.all():
                price_types.append(
                    PriceType(
                        price_type=pri, product=product,
                        dealer_status=sta
                    )
                )
        PriceType.objects.bulk_create(price_types)

        prod_price_data = []
        for c in p.get('Prices'):
            price_type = PriceType.objects.filter(uid=c.get('PricetypesUID')).first()
            if price_type:
                dealer_statuses = DealerStatus.objects.all()

                for status in dealer_statuses:
                    prod_price = ProductPrice.objects.filter(price_type=price_type, product=product,
                                                             dealer_status=status)
                    amount = int(c.get('PriceAmount'))
                    prod_price.price = amount

                    prod_price_data.append(prod_price)

        ProductPrice.objects.bulk_update(prod_price_data, ['price'])




