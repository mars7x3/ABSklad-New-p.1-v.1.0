import datetime
import json
from uuid import uuid4

import requests
from django.db import transaction
from django.utils import timezone

from account.models import DealerStatus, MyUser, Wallet, DealerProfile
from account.utils import generate_pwd
from general_service.models import Stock, City, PriceType, CashBox
from one_c.models import MoneyDoc
from order.models import MyOrder, OrderProduct
from product.models import AsiaProduct, Category, ProductCount, ProductPrice, Collection


def sync_prods_list():
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
        if product:
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
                    village=city.first(),
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
                        'total_price': d.get('total_price') if d.get('total_price') else 0,
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


def sync_order_to_1C(order):
    try:
        with transaction.atomic():
            url = "http://91.211.251.134/ab1c/hs/asoi/CreateSale"
            products = order.order_products.all()
            released_at = timezone.localtime(order.released_at)
            money = order.money_docs.filter(is_active=True).first()
            payload = json.dumps({
                "user_uid": order.author.uid,
                "created_at": f'{released_at}',
                "payment_doc_uid": money.uid,
                "cityUID": order.city_stock.stocks.first().uid,
                "products": [
                    {"title": p.title,
                     "uid": p.uid,
                     "count": int(p.count),
                     'price': int(p.price)}
                    for p in products
                ]
            })

            username = 'Директор'
            password = '757520ля***'
            print('***ORDER CREATE***')
            print(payload)
            response = requests.request("POST", url, data=payload, auth=(username.encode('utf-8'), password.encode('utf-8')))
            print(response.text)
            response_data = json.loads(response.content)

            uid = response_data.get('result_uid')
            order.uid = uid
            order.save()
    except Exception as e:
        raise TypeError


def sync_order_pay_to_1C(order):
    try:
        with transaction.atomic():

            url = "http://91.211.251.134/ab1c/hs/asoi/CreateaPyment"
            if 'Наличка' == order.type_status or order.type_status == 'Каспи':
                type_status = 'Наличка'
                cash_box_uid = order.author.city.cash_boxs.first().uid
            else:
                type_status = 'Без нал'
                cash_box_uid = ''
            payload = json.dumps({
                "user_uid": order.author.uid,
                "amount": int(order.price),
                "created_at": f'{timezone.localtime(order.created_at)}',
                "order_type": type_status,
                "cashbox_uid": cash_box_uid,
            })
            print('***ORDER PAY***')
            print('sync_order_pay_to_1C: ', payload)
            username = 'Директор'
            password = '757520ля***'
            response = requests.request("POST", url, data=payload, auth=(username.encode('utf-8'), password.encode('utf-8')))
            print('1C return - ', response.text)

            response_data = json.loads(response.content)
            payment_doc_uid = response_data.get('result_uid')
            order.payment_doc_uid = payment_doc_uid
            order.save()
            MoneyDoc.objects.create(order=order, user=order.author, amount=order.price, uid=payment_doc_uid)

    except Exception as e:
        raise TypeError


def sync_1c_money_doc(money_doc):
    url = "http://91.211.251.134/ab1c/hs/asoi/CreateaPyment"
    if money_doc.status == 'Без нал':
        cash_box_uid = ''
    else:
        city = money_doc.user.dealer_profile.village.city
        cash_box = city.stocks.first().cash_boxs.first()
        cash_box_uid = cash_box.uid
    # TODO: если в регионе будет больше 1 склада, то надо будет логику кассы поменять.

    payload = json.dumps({
        "user_uid": money_doc.user.uid,
        "amount": int(money_doc.amount),
        "created_at": f'{timezone.localtime(money_doc.created_at)}',
        "order_type": money_doc.status,
        "cashbox_uid": cash_box_uid,

    })
    print('***Sync_order_pay_to_1C: ', payload)

    username = 'Директор'
    password = '757520ля***'
    response = requests.request("POST", url, data=payload, auth=(username.encode('utf-8'), password.encode('utf-8')))
    print('return - ', response.text)
    response_data = json.loads(response.content)
    uid = response_data.get('result_uid')

    money_doc.uid = uid
    money_doc.save()


def sync_return_order_to_1C(returns_order):
    url = "http://91.211.251.134/ab1c/hs/asoi/ReturnGoods"
    products = returns_order.return_products.all()
    payload = json.dumps({
        "uid": returns_order.order.uid,
        "created_at": f'{timezone.localtime(returns_order.created_at)}',
        "products_return": [
            {
                "uid": p.product.uid,
                "count": int(p.count),
            }
            for p in products
        ]
    })

    username = 'Директор'
    password = '757520ля***'
    response = requests.request("POST", url, data=payload, auth=(username.encode('utf-8'), password.encode('utf-8')))


def sync_dealer_back_to_1C(dealer):
    url = "http://91.211.251.134/ab1c/hs/asoi/clients"
    profile = dealer.dealer_profile
    payload = json.dumps({
        "clients": [{
            'Name': dealer.name,
            'UID': dealer.uid,
            'Telephone': dealer.phone,
            'Address': dealer.address,
            'Liability': profile.liability,
            'Email': dealer.email,
            'City': profile.village.city.title,
            'CityUID': profile.village.city.user_uid,
        }]})
    username = 'Директор'
    password = '757520ля***'
    print('***DEALER SYNC***')
    print(payload)
    response = requests.request("POST", url, data=payload, auth=(username.encode('utf-8'), password.encode('utf-8')))
    print(response.text)
    response_data = json.loads(response.content)

    dealer_uid = response_data.get('client')
    if dealer_uid:
        dealer.uid = dealer_uid
        dealer.save()


def sync_product_crm_to_1c(product):
    url = "http://91.211.251.134/ab1c/hs/asoi/GoodsCreate"
    payload = json.dumps({
        "NomenclatureName": product.title,
        "NomenclatureUID": product.uid,
        "CategoryName": product.category.title,
        "CategoryUID": product.category.uid,
        "Prices": [
            {
                "PriceTypes": p.city.title,
                "PricetypesUID": p.city.price_uid,
                "PriceAmount": int(p.price)
            }
            for p in product.prices.filter(dealer_status__discount=0)
        ]
    })
    username = 'Директор'
    password = '757520ля***'
    print('***PRODUCT SYNC***')
    print(payload)
    response = requests.request("POST", url, data=payload, auth=(username.encode('utf-8'), password.encode('utf-8')))
    print(response.text)
    response_data = json.loads(response.content)
    product_uid = response_data.get('NomenclatureUID')
    product.uid = product_uid
    product.save()


def sync_dealer_1C_to_back(request):
    data = {
        "name": request.data.get("Name"),
        "uid": request.data.get("UID"),
        "phone": request.data.get("Telephone"),
        "email": request.data.get("Email"),
        'status': 'dealer_1c',
        'password': generate_pwd(),
    }
    profile_data = {
        "liability": request.data.get('Liability'),
        "address": request.data.get("Address"),
    }
    if len(data.get('email')) < 6:
        data['email'] = str(uuid4()) + '@absklad.com'

    city = City.objects.filter(user_uid=request.data.get('CityUID')).first()
    if city:
        village = city.villages.first()
        profile_data['village'] = village
        data['is_active'] = True
    else:
        data['is_active'] = False
        profile_data['village'] = None

    user = MyUser.objects.filter(uid=request.data.get('UID')).first()
    if user:
        user.name = data['name']
        user.uid = data['uid']
        user.phone = data['phone']
        user.email = data['email']
        user.save()

        profile = user.dealer_profile
        profile.liability = profile_data['liability']
        profile.village = profile_data['village']
        profile.address = profile_data['address']
        profile.save()

    else:
        user = MyUser.objects.create(**data)
        DealerProfile.objects.create(**profile_data)

    Wallet.objects.get_or_create(user=user)


def sync_category_crm_to_1c(category):
    url = "http://91.211.251.134/ab1c/hs/asoi/CategoryGoodsCreate"
    payload = json.dumps({
        "category_title": category.title,
        "category_uid": category.uid,
    })

    username = 'Директор'
    password = '757520ля***'
    response = requests.request("POST", url, data=payload, auth=(username.encode('utf-8'), password.encode('utf-8')))
    response_data = json.loads(response.content)
    uid = response_data.get('category_uid')

    category.uid = uid
    category.save()


def sync_category_1c_to_crm(data):
    category = Category.objects.filter(uid=data.get('category_uid')).first()
    if category:
        category.title = data.get('category_title')
        category.save()
    else:
        Category.objects.create(title=data.get('category_title'), uid=data.get('category_uid'),
                                slug=data.get('category_uid'))

