import datetime
import json
from uuid import uuid4

import requests
from django.db import transaction
from django.db.models import F, Case, When, Value, IntegerField
from django.utils import timezone
from transliterate import translit

from account.models import DealerStatus, MyUser, Wallet, DealerProfile, Notification
from account.utils import generate_pwd
from crm_kpi.utils import update_dealer_kpi_by_order
from crm_stat.tasks import main_stat_order_sync, main_stat_pds_sync
from general_service.models import Stock, City, PriceType, CashBox
from one_c.models import MoneyDoc
from order.models import MyOrder, OrderProduct
from product.models import AsiaProduct, Category, ProductCount, ProductPrice, Collection, ProductCostPrice


def total_cost_price(products):
    amount = 0
    for p in products:
        product = AsiaProduct.objects.filter(
            uid=p.get('uid')
        ).annotate(
            cost_price=Case(
                When(cost_prices__is_active=True, then=F('cost_prices__price')),
                default=Value(0),
                output_field=IntegerField()
            )
        ).first()
        if product:
            amount += product.cost_price * int(p.get('count'))

    return round(amount)


def plus_quantity(order):
    products_data = order.order_products.all().values_list('ab_product_id', 'count')
    update_data = []
    for p_id, count in products_data:
        quantity = ProductCount.objects.filter(product_id=p_id, stock=order.stock).first()
        if quantity:
            quantity.count_crm += count
            update_data.append(quantity)
    ProductCount.objects.bulk_update(update_data, ['count_crm'])


def generate_products_data(products):
    result = []
    for p in products:
        product = AsiaProduct.objects.get(uid=p.get('uid'))
        total_price = int(p.get('price')) * int(p.get('count'))
        cost_price = product.cost_prices.filter(is_active=True).first()
        result.append({'title': product.title, 'category': product.category, 'count': int(p.get('count')),
                       'ab_product': product, 'total_price': total_price, 'price': int(p.get('price')),
                       'cost_price': cost_price.price})
    return result


def minus_quantity(order):
    products_data = order.order_products.all().values_list('ab_product_id', 'count')
    update_data = []
    for p_id, count in products_data:
        quantity = ProductCount.objects.filter(product_id=p_id, stock=order.stock).first()
        if quantity:
            quantity.count_crm -= count
            update_data.append(quantity)
    ProductCount.objects.bulk_update(update_data, ['count_crm'])


def sync_prods_list():
    url = 'http://91.211.251.134/testcrm/hs/asoi/leftovers'
    username = 'Директор'
    password = '757520ля***'
    response = requests.get(url, auth=(username.encode('utf-8'), password.encode('utf-8')))
    data = json.loads(response.content)

    products = data.get('products')
    print(len(products))
    x = 0

    collection = Collection.objects.filter(slug='asiabrand').first()
    cost_price_create = []
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
                cost_price_create.append(ProductCostPrice(product=product))
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
        city_price = []
        for sta in DealerStatus.objects.all():
            for pri in PriceType.objects.all():
                price_types.append(
                    ProductPrice(
                        price_type=pri, product=product,
                        d_status=sta
                    )
                )
            for cit in City.objects.all():
                city_price.append(
                    ProductPrice(
                        city=cit, product=product,
                        d_status=sta
                    )
                )
        ProductPrice.objects.bulk_create(price_types)
    ProductCostPrice.objects.bulk_create(product=product)

        # prod_price_data = []
        # for c in p.get('Prices'):
        #     price_type = PriceType.objects.filter(uid=c.get('PricetypesUID')).first()
        #     if price_type:
        #         dealer_statuses = DealerStatus.objects.all()
        #
        #         for status in dealer_statuses:
        #             prod_price = ProductPrice.objects.filter(price_type=price_type, product=product,
        #                                                      d_status=status).first()
        #             amount = int(c.get('PriceAmount'))
        #             prod_price.price = amount
        #
        #             prod_price_data.append(prod_price)
        #
        # ProductPrice.objects.bulk_update(prod_price_data, ['price'])


def sync_prod_crud_1c_crm(data):  # sync product 1C -> CRM
    print('***Product CRUD***')
    print(data)
    dealer_statuses = DealerStatus.objects.all()
    cities = City.objects.all()
    p_types = PriceType.objects.all()

    price_create = []
    cost_price_create = []
    uid = data.get('product_uid')
    product = AsiaProduct.objects.filter(uid=uid).first()
    if product:
        category = Category.objects.filter(uid=data.get('category_uid'))
        if category:
            product.category = category.first()

        product.title = data.get('title')
        product.is_active = bool(int(data.get('is_active')))
        product.vendor_code = data.get('vendor_code')
        product.save()

    else:
        product = AsiaProduct.objects.create(uid=uid, title=data.get('title'),
                                             is_active=bool(int(data.get('is_active'))),
                                             vendor_code=data.get('vendor_code'))
        ProductCostPrice.objects.create(product=product)
        category = Category.objects.filter(uid=data.get('category_uid')).first()
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


def sync_dealer_update():
    url = 'http://91.211.251.134/testcrm/hs/asoi/clients'
    username = 'Директор'
    password = '757520ля***'
    response = requests.get(url, auth=(username.encode('utf-8'), password.encode('utf-8')))
    response_data = json.loads(response.content)

    clients = response_data.get('clients')
    dealer_data = []
    count = 0
    for c in clients:
        count += 1
        print(count)
        user = MyUser.objects.filter(uid=c.get('UID')).first()
        if user:
            city = City.objects.filter(user_uid=c.get('CityUID')).first()
            if city:
                profile = user.dealer_profile
                village = city.villages.first()
                profile.village = village
                dealer_data.append(profile)

    DealerProfile.objects.bulk_update(dealer_data, ['village'])


def sync_dealer():
    url = 'http://91.211.251.134/testcrm/hs/asoi/clients'
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
            if city:
                village = city.villages.first()
            else:
                village = None
            dealer_status = d.pop('dealer_status')
            user = MyUser.objects.create_user(**d)
            dealer_data.append(
                DealerProfile(
                    user=user,
                    village=village,
                    dealer_status=dealer_status,
                    price_type=price_type,
                    price_city=city
                )
            )
            wallet_data.append(user)

    DealerProfile.objects.bulk_create(dealer_data)

    wallet_r = []
    for deal in wallet_data:
        wallet_r.append(Wallet(dealer=deal.dealer_profile))

    Wallet.objects.bulk_create(wallet_r)


def sync_order_histories_1c_to_crm():
    url = 'http://91.211.251.134/testcrm/hs/asoi/GetSale'
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
                            'created_at': datetime.datetime.strptime(o.get('created_at'), "%d.%m.%Y %H:%M:%S") - datetime.timedelta(hours=6),
                            'released_at': datetime.datetime.strptime(o.get('created_at'), "%d.%m.%Y %H:%M:%S") - datetime.timedelta(hours=6),
                            'paid_at': datetime.datetime.strptime(o.get('created_at'), "%d.%m.%Y %H:%M:%S") - datetime.timedelta(hours=6),
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
            order.created_at = datetime.datetime.strptime(o.get('created_at'), "%d.%m.%Y %H:%M:%S") - datetime.timedelta(hours=6)
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
        date_object = datetime.datetime.strptime(p['created_at'], "%d.%m.%Y %H:%M:%S") - datetime.timedelta(hours=6)
        money_doc = MoneyDoc.objects.filter(uid=p['uid']).first()
        if money_doc:
            money_doc.created_at = date_object
            update_data.append(money_doc)

    MoneyDoc.objects.bulk_update(update_data, ['created_at'])


def sync_1c_money_doc_crud(data):
    money_doc = MoneyDoc.objects.filter(uid=data.get('doc_uid')).first()
    user = MyUser.objects.filter(uid=data.get('user_uid')).first()
    cash_box = CashBox.objects.filter(uid=data.get('kassa')).first()
    if not user:
        print('Контрагент не существует')
        return False, 'Контрагент не существует'
    if not cash_box:
        print('Касса не существует')
        return False, 'Касса не существует'
    if money_doc:
        money_doc.status = data.get('doc_type')
        money_doc.is_active = bool(int(data.get('is_active')))
        money_doc.amount = data.get('amount')
        money_doc.created_at = datetime.datetime.strptime(data.get('created_at'), '%Y-%m-%d %H:%M:%S') - datetime.timedelta(hours=6)
        money_doc.save()
        if bool(int(data.get('is_active'))) == money_doc.is_active:
            money_doc.is_checked = not money_doc.is_checked
            money_doc.save()
            print('Check stat')
            main_stat_order_sync(money_doc)
            print('End Check stat')
            money_doc.is_checked = not money_doc.is_checked
            money_doc.save()
            print(money_doc.is_checked)


    else:
        data = {
            'uid': data.get('doc_uid'),
            'user': user,
            'cash_box': cash_box,
            'status': data.get('doc_type'),
            'is_active': bool(int(data.get('is_active'))),
            'amount': data.get('amount'),
            'created_at': datetime.datetime.strptime(data.get('created_at'), '%Y-%m-%d %H:%M:%S') - datetime.timedelta(hours=6)
        }
        money_doc = MoneyDoc.objects.create(**data)
        print('Check stat')
        main_stat_pds_sync(money_doc)
        print('End Check stat')
        money_doc.is_checked = not money_doc.is_checked
        money_doc.save()
        print(money_doc.is_checked)

    return True, 'Success!'


def sync_dealer_1C_to_back(request):
    data = {
        "name": request.data.get("Name"),
        "username": request.data.get("UID"),
        "uid": request.data.get("UID"),
        "phone": request.data.get("Telephone"),
        "email": request.data.get("Email"),
        'status': 'dealer',
        'password': generate_pwd(),
        'is_active': bool(int(request.data.get('is_active')))
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
    else:
        data['is_active'] = False
        profile_data['village'] = None

    user = MyUser.objects.filter(uid=request.data.get('UID')).first()
    if user:
        user.name = data['name']
        user.uid = data['uid']
        user.phone = data['phone']
        user.email = data['email']
        user.is_active = data['is_active']
        user.save()

        profile = user.dealer_profile
        profile.liability = profile_data['liability']
        profile.village = profile_data['village']
        profile.address = profile_data['address']
        profile.save()

    else:
        profile_data['is_active'] = False
        user = MyUser.objects.create_user(**data)
        profile = DealerProfile.objects.create(user=user, **profile_data)

    Wallet.objects.get_or_create(dealer=profile)


def sync_category_1c_to_crm(data):
    category = Category.objects.filter(uid=data.get('category_uid')).first()
    if category:
        category.title = data.get('category_title')
        category.is_active = bool(int(data.get('is_active')))
        category.save()
    else:
        Category.objects.create(title=data.get('category_title'), uid=data.get('category_uid'),
                                slug=data.get('category_uid'), is_active=bool(int(data.get('is_active'))))


def order_1c_to_crm(data):
    order_data = dict()
    products = data.get('products')
    user = MyUser.objects.get(uid=data.get('user_uid'))
    city_stock = Stock.objects.filter(uid=data.get('cityUID')).first()

    if user and city_stock:
        order_data['author'] = user.dealer_profile
        order_data['cost_price'] = total_cost_price(products)
        order_data['status'] = 'sent'
        order_data['uid'] = data.get('order_uid')
        order_data['price'] = data.get('total_price')
        order_data['type_status'] = 'wallet'
        order_data['stock'] = city_stock
        order_data['created_at'] = datetime.datetime.strptime(data.get('created_at'), "%d.%m.%Y %H:%M:%S") - datetime.timedelta(hours=6)
        order_data['released_at'] = datetime.datetime.strptime(data.get('created_at'), "%d.%m.%Y %H:%M:%S") - datetime.timedelta(hours=6)
        order_data['paid_at'] = datetime.datetime.strptime(data.get('created_at'), "%d.%m.%Y %H:%M:%S") - datetime.timedelta(hours=6)
        order_data['is_active'] = bool(int(data['is_active']))

        order = MyOrder.objects.filter(uid=data.get("order_uid")).first()
        if order:
            # update
            order_data.pop('paid_at')
            order_data.pop('created_at')

            if order.is_active:
                plus_quantity(order)

            for key, value in order_data.items():
                setattr(order, key, value)

            order.save()

            if order.is_active:
                order.order_products.all().delete()
                products_data = generate_products_data(products)
                OrderProduct.objects.bulk_create([OrderProduct(order=order, **i) for i in products_data])
                minus_quantity(order)

            main_stat_order_sync(order)
            update_data = []
            for p in order.order_products.all():
                p.is_checked = not p.is_checked
                update_data.append(p)
            OrderProduct.objects.bulk_update(update_data, ['is_checked'])

        else:
            # create order
            order = MyOrder.objects.create(**order_data)

            products_data = generate_products_data(products)
            OrderProduct.objects.bulk_create([OrderProduct(order=order, **i) for i in products_data])
            minus_quantity(order)

            main_stat_order_sync(order)
            update_data = []
            for p in order.order_products.all():
                p.is_checked = not p.is_checked
                update_data.append(p)
            OrderProduct.objects.bulk_update(update_data, ['is_checked'])

            kwargs = {'user': user, 'title': f'Заказ #{order.id}', 'description': order.comment,
                      'link_id': order.id, 'status': 'order', 'is_push': True}
            Notification.objects.create(**kwargs)

            # change_dealer_status.delay(user.id)



def sync_test_nurs():
    url = "http://91.211.251.134/testcrm/hs/asoi/GoodsCreate"
    payload = json.dumps({
        "NomenclatureName": 'Nurs, eto tovar!',
        "NomenclatureUID": '2dfcc1c2-1c86-11ed-8a2f-2c59e53ae4c3',
        "CategoryName": 'Nurs eto category!',
        "CategoryUID": '65265414-1c85-11ed-8a2f-2c59e53ae4c3',
        "is_product": 0,
        # "uid": ""
    })
    username = 'Директор'
    password = '757520ля***'
    print('***PRODUCT SYNC***')
    print(payload)
    response = requests.request("POST", url, data=payload, auth=(username.encode('utf-8'), password.encode('utf-8')))
    print(response.text)
    print(response.status_code)


def sync_1c_price_city_crud(data):
    city = City.objects.filter(price_uid=data['uid']).first()
    price_type = PriceType.objects.filter(uid=data['uid']).first()

    if city:
        city.is_active = bool(int(data['is_active']))
        city.title = data['title']
        city.save()
    elif price_type:
        price_type.is_active = bool(int(data['is_active']))
        price_type.title = data['title']
        price_type.save()
    else:
        data = {
            'uid': data['uid'],
            'title': data['title'],
            'is_active': bool(int(data['is_active']))
        }
        PriceType.objects.create(**data)
    return True, 'Success!'


def sync_1c_user_city_crud(data):
    city = City.objects.filter(user_uid=data['uid']).first()
    title = translit(data['title'], 'ru', reversed=True)
    slug = title.replace(' ', '_').lower()
    if city:
        city.is_active = bool(int(data['is_active']))
        city.title = data['title']
        city.slug = slug
        city.save()
    else:
        data = {
            'uid': data['uid'],
            'title': data['title'],
            'is_active': bool(int(data['is_active'])),
            'slug': slug
        }
        City.objects.create(**data)
    return True, 'Success!'


def sync_1c_stock_crud(data):
    stock = Stock.objects.filter(uid=data['uid']).first()
    if stock:
        stock.is_active = bool(int(data['is_active']))
        stock.title = data['title']
        stock.save()
    else:
        data = {
            'uid': data['uid'],
            'title': data['title'],
            'is_active': bool(int(data['is_active'])),
        }
        Stock.objects.create(**data)
    return True, 'Success!'


def sync_1c_prod_count_crud(data):
    product = AsiaProduct.objects.filter(uid=data['uid']).first()
    if product:
        update_data = []
        for p in data['products']:
            stock = Stock.objects.filter(uid=p['stock_uid']).first()
            count = product.counts.filter(stock=stock)
            if stock:
                count.count_1c = p['count']
                update_data.append(count)
            else:
                return False, 'Склад не найден!'
        ProductCount.objects.bulk_update(update_data, ['count_1c'])
        return True, 'Success!'
    else:
        return False, 'Продукт не найден!'


def sync_1c_prod_price_crud(data):
    product = AsiaProduct.objects.filter(uid=data['uid']).first()
    d_status = DealerStatus.objects.filter(discount=0).first()
    if product:
        price_type_data = []
        city_data = []

        for p in data['products']:
            price_type = PriceType.objects.filter(uid=p['city_uid']).first()
            city = City.objects.filter(price_uid=p['city_uid']).first()
            if price_type:
                price = product.prices.filter(d_status=d_status, price_type=price_type).first()
                price.price = p['amount']
                price_type_data.append(price)
            elif city:
                price = product.prices.filter(d_status=d_status, city=city).first()
                price.price = p['amount']
                city_data.append(price)
            else:
                return False, 'Город не найден!'
        if price_type_data:
            ProductPrice.objects.bulk_update(price_type_data, ['price'])
        elif city_data:
            ProductPrice.objects.bulk_update(city_data, ['price'])
        return True, 'Success!'
    else:
        return False, 'Продукт не найден!'

