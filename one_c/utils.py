import datetime
import json

import requests

from account.models import DealerStatus, MyUser, Wallet, DealerProfile
from general_service.models import Stock, City, PriceType, CashBox
from one_c.models import MoneyDoc
from order.models import MyOrder, OrderProduct
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


def sync_prod_crud_1c_crm(request):  # sync product 1C -> CRM
    products = request.data.get('products')
    print('***Product CRUD***')
    print(products)
    dealer_statuses = DealerStatus.objects.all()
    cities = City.objects.all()
    p_types = PriceType.objects.all()

    price_create = []

    for prod in products:
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

            for d in dealer_statuses:
                for c in cities:
                    price_create.append(ProductPrice(city=c, product=product, d_status=d))
            for d in dealer_statuses:
                for t in p_types:
                    price_create.append(ProductPrice(price_type=t, product=product, d_status=d))

            p_count_data = [ProductCount(stock=s, product=product) for s in Stock.objects.all()]
            ProductCount.objects.bulk_create(p_count_data)

    ProductPrice.objects.bulk_create(price_create)


def sync_dealer():
    url = 'http://91.211.251.134/ab1c/hs/asoi/clients'
    username = 'Директор'
    password = '757520ля***'
    response = requests.get(url, auth=(username.encode('utf-8'), password.encode('utf-8')))
    response_data = json.loads(response.content)

    clients = response_data.get('clients')
    dealer_status = DealerStatus.objects.filter(title='C').first()
    data = []
    count = 0
    for c in clients:
        count += 1
        print(count)
        user = MyUser.objects.filter(uid=c.get('UID'))
        if not user:
            city = City.objects.filter(user_uid=c.get('CityUID')).first()
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
                     'city': city if city else None
                     }
            data.append(dict_)

    dealer_data = []
    wallet_data = []
    if data:
        for d in data:
            if d['city']:
                city = d['city'].title
            else:
                city = ''

            price_type = PriceType.objects.filter(title__icontains=city).first()
            city = d.pop('city')
            dealer_status = d.pop('dealer_status')
            user = MyUser.objects.create_user(**d)
            dealer_data.append(
                DealerProfile(
                    user=user,
                    village__city=city,
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


def sync_order_histories_1c_to_crm():
    url = 'http://91.211.251.134/ab1c/hs/asoi/GetSale'
    username = 'Директор'
    password = '757520ля***'
    response = requests.get(url, auth=(username.encode('utf-8'), password.encode('utf-8')))
    response_data = json.loads(response.content)

    orders = response_data.get('orders')

    data_order_products = []
    data_orders = []

    x = 0
    for o in orders:
        x += 1
        print('* ', x)
        order = MyOrder.objects.filter(uid=o.get('uid'))
        if not order:
            author = MyUser.objects.filter(uid=o.get('author_uid'), is_active=True).first()
            if author:
                stock = Stock.objects.filter(uid=o.get('city_uid')).first()
                if stock:
                    data_orders.append(
                        {
                            'author': author.dealer_profile,
                            'price': o.get('total_price'),
                            'type_status': o.get('type_status') if o.get('type_status') else 'Карта',
                            'created_at': datetime.datetime.strptime(o.get('created_at'), "%d.%m.%Y %H:%M:%S"),
                            'released_at': datetime.datetime.strptime(o.get('created_at'), "%d.%m.%Y %H:%M:%S"),
                            'paid_at': datetime.datetime.strptime(o.get('created_at'), "%d.%m.%Y %H:%M:%S"),
                            'uid': o.get('uid'),
                            'status': 'success',
                            'stock': stock,
                        }
                    )
                    for p in o.get('products'):
                        data_order_products.append(
                            {
                                'order': o.get('uid'),
                                'count': p.get('count'),
                                'total_price': p.get('sum'),
                                'price': p.get('price'),
                                'uid': p.get('uid')

                            }
                        )
    MyOrder.objects.bulk_create([MyOrder(**i) for i in data_orders])

    res_data = []
    x = 0
    for d in data_order_products:
        x += 1
        print(x)
        p = AsiaProduct.objects.filter(uid=d.get('uid')).first()
        order = MyOrder.objects.filter(uid=d['order']).first()
        if order:
            if p:
                res_data.append(
                    {
                        'order': order,
                        'category': p.category,
                        'title': p.title,
                        'total_price': d.get('sum') if d.get('sum') else 0 ,
                        'count': d.get('count') if d.get('count') else 0,
                        'price': d.get('price') if d.get('price') else 0,
                        'ab_product': p,
                    }
                )

    OrderProduct.objects.bulk_create([OrderProduct(**i) for i in res_data])

    x = 0
    for o in orders:
        x += 1
        print('*** ', x)
        order = MyOrder.objects.filter(uid=o.get('uid')).first()
        if order:
            order.created_at = datetime.datetime.strptime(o.get('created_at'), "%d.%m.%Y %H:%M:%S")
            order.save()


def sync_pay_doc_histories():
    url = 'http://91.211.251.134/testcrm/hs/asoi/GetPyments'
    username = 'Директор'
    password = '757520ля***'
    response = requests.get(url, auth=(username.encode('utf-8'), password.encode('utf-8')))
    response_data = json.loads(response.content)

    payments = response_data.get('pyments')

    data_payment = []

    for p in payments:
        user = MyUser.objects.filter(uid=p['user_uid']).first()
        cashbox_uid = CashBox.objects.filter(uid=p['cashbox_uid']).first()
        if user and cashbox_uid:
            data_payment.append(MoneyDoc(
                status=p['order_type'],
                user=user,
                amount=p['amount'],
                cash_box=cashbox_uid,
                uid=p['uid'],
            ))
    MoneyDoc.objects.bulk_create(data_payment)

    update_data = []
    for p in payments:
        date_object = datetime.datetime.strptime(p['created_at'], "%d.%m.%Y %H:%M:%S")
        money_doc = MoneyDoc.objects.filter(uid=p['uid']).first()
        if money_doc:
            money_doc.created_at = date_object
            update_data.append(money_doc)

    MoneyDoc.objects.bulk_update(update_data, ['created_at'])


