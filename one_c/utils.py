import json

import requests

from account.models import DealerStatus, MyUser, Wallet, DealerProfile
from general_service.models import Stock, City, PriceType
from product.models import AsiaProduct, Category, ProductCount, ProductPrice, Collection


def synchronization_back_to_1C():
    url = 'http://91.211.251.134/ab1c/hs/asoi/leftovers'
    username = 'Директор'
    password = '757520ля***'
    response = requests.get(url, auth=(username.encode('utf-8'), password.encode('utf-8')))
    data = json.loads(response.content)

    products = data.get('products')
    print(len(products))
    x = 0

    collection = Collection.objects.filter(slug='asiabrand').first()

    for p in products:
        x += 1
        print(x)
        product = AsiaProduct.objects.filter(uid=p.get('NomenclatureUID')).first()
        if product:
            product = product
            product.title = (p.get('NomenclatureName'))
            product.collection = collection
            product.save()

        if not product:
            category = Category.objects.filter(uid=p['CategoryUID']).first()
            if category:
                product = AsiaProduct.objects.create(uid=p.get('NomenclatureUID'), title=p.get('NomenclatureName'),
                                                     category=category, collection=collection)
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
        ProductCount.objects.bulk_update(prod_count_data, ['count_1c', 'count_crm', 'count_norm'])

        price_types = []
        for pri in PriceType.objects.all():
            for sta in DealerStatus.objects.all():
                price_types.append(
                    ProductPrice(
                        price_type=pri, product=product,
                        d_status=sta
                    )
                )
        ProductPrice.objects.bulk_create(price_types)

        prod_price_data = []
        for c in p.get('Prices'):
            price_type = PriceType.objects.filter(uid=c.get('PricetypesUID')).first()
            if price_type:
                dealer_statuses = DealerStatus.objects.all()

                for status in dealer_statuses:
                    prod_price = ProductPrice.objects.filter(price_type=price_type, product=product,
                                                             d_status=status).first()
                    amount = int(c.get('PriceAmount'))
                    prod_price.price = amount

                    prod_price_data.append(prod_price)

        ProductPrice.objects.bulk_update(prod_price_data, ['price'])


def synchronization_1C_to_back(request):  # sync product 1C -> CRM
    products = request.data.get('products')
    print('***Product CRUD***')
    print(products)
    for prod in products:
        prices_1c = prod.get('prices')
        uid = prod.get('product_uid')
        product = AsiaProduct.objects.filter(uid=uid).first()
        is_new = True
        if product:
            is_new = False
            product.title = prod.get('title')
            product.save()
            if product.category:
                if product.category.uid != prod.get('category_uid'):
                    category = Category.objects.filter(uid=prod.get('category_uid'))
                    if category:
                        product.category = category.first()
                        product.save()

        else:
            product = AsiaProduct.objects.create(uid=uid, title=prod.get('title'))
            category = Category.objects.filter(uid=prod.get('category_uid')).first()
            if category:
                product.category = category
                product.save()

        if prices_1c:
            for p in prices_1c:
                price_type = PriceType.objects.filter(uid=p.get('city_uid')).first()
                if price_type:
                    dealer_statuses = DealerStatus.objects.all()

                    for status in dealer_statuses:
                        price = ProductPrice.objects.filter(price_type=price_type, product=product,
                                                            d_status=status).first()
                        amount = int(p.get('price'))
                        if price:
                            price.price = amount
                            price.save()
                        else:
                            ProductPrice.objects.create(price_type=price_type, product=product, price=amount,
                                                        d_status=status)

        if is_new:
            product.counts.all().delete()
            p_count_data = [ProductCount(stock=s, product=product) for s in Stock.objects.all()]
            ProductCount.objects.bulk_create([ProductCount(**i) for i in p_count_data])


def sync_dealer():
    url = 'http://91.211.251.134/ab1c/hs/asoi/clients'
    username = 'Директор'
    password = '757520ля***'
    response = requests.get(url, auth=(username.encode('utf-8'), password.encode('utf-8')))
    response_data = json.loads(response.content)

    clients = response_data.get('clients')
    dealer_status = DealerStatus.objects.filter(title='C')
    data = []
    count = 0
    for c in clients:
        count += 1
        print(count)
        user = MyUser.objects.filter(uid=c.get('UID'))
        if not user:

            password = 'absklad123'
            dict_ = {'name': c.get('Name'),
                     'uid': c.get('UID'),
                     'phone': c.get('Telephone'),
                     'email': c.get('UID') + "@absklad.com",
                     'password': password,
                     'pwd': password,
                     'status': 'dealer',
                     'dealer_status': dealer_status,
                     'username': c.get('UID'),
                     }

            city = City.objects.filter(user_uid=c.get('CityUID')).first()
            if city:
                dict_['city'] = city
            else:
                dict_['is_active'] = False

            data.append(dict_)

    dealer_data = []
    wallet_data = []
    if data:
        for d in data:
            price_type = PriceType.objects.filter(title__icontains=d['city'].title)
            city = d.pop('city')
            dealer_status = d.pop('dealer_status')
            user = MyUser.objects.create_user(**d)
            dealer_data.append(
                DealerProfile(
                    user=user,
                    city=city,
                    dealer_status=dealer_status,
                    price_type=price_type

                )
            )
            wallet_data.append(user)

    DealerProfile.objects.bulk_create(dealer_data)

    wallet_r = []
    for deal in wallet_data:
        wallet_r.append(Wallet(dealer=deal.dealer_profile))
    Wallet.objects.bulk_create(wallet_r)


