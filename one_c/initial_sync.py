import datetime
import json

import requests
from decouple import config
from django.db import connection, transaction

from absklad_commerce.celery import app
from account.models import DealerStatus, MyUser, DealerProfile, Wallet
from general_service.models import Stock, PriceType, City, CashBox, Village
from one_c.models import MoneyDoc
from order.models import MyOrder, OrderProduct
from product.models import Collection, AsiaProduct, Category, ProductCostPrice, ProductCount, ProductPrice


"""
http://91.211.251.134/testcrm/hs/asoi/Warehouses метод гет на получение складов 
{
    "Warehouses": [
        {
            "is_active": 1,
            "title": "Склад \"СМ - № 01 Подвал\"",
            "uid": "695614ea-17a7-11ed-8a2f-2c59e53ae4c3"
        },

http://91.211.251.134/testcrm/hs/asoi/CreateInventory get метод получение всех списков инвентаризаций
http://91.211.251.134/testcrm/hs/asoi/movements get получения перемещений

http://91.211.251.134/testcrm/hs/asoi/PriceTypes метод гет на получение типы ценов
{
    "PriceTypes": [
        {
            "is_active": 1,
            "title": "Плановая",
            "uid": "51607f89-1c76-11ed-8a2f-2c59e53ae4c3"
        },
        
http://91.211.251.134/testcrm/hs/asoi/ClientCities метод гетуха Для получения городов клиента


"""


def main_initial_sync():
    # Collection.objects.create(title='ASIABRAND', slug='asiabrand')
    # DealerStatus.objects.create(title='C', is_active=True)
    cities = [
        City(title='Шымкент', user_uid='a7732ddf-2e71-11ed-8a2f-2c59e53ae4c3',
             slug='shymkent', price_uid='37c308db-1f17-11ee-8a38-2c59e53ae4c2'),
        City(title='Кызылорда', user_uid='215eba93-3407-11ed-8a2f-2c59e53ae4c3',
             slug='kyzylorda', price_uid='07d8ff4c-1f17-11ee-8a38-2c59e53ae4c2'),
        City(title='ГП', user_uid='dc448280-350e-11ee-8a39-2c59e53ae4c3',
             slug='gp', price_uid='37bb3aee-3d5c-11ed-8a2f-2c59e53ae4c3'),
        City(title='Алматы', user_uid='1c114565-9b0d-11ed-8a30-2c59e53ae4c2',
             slug='almaty', price_uid='f16eb774-1f15-11ee-8a38-2c59e53ae4c2'),
        City(title='Астана', user_uid='7400e4a9-37fc-11ed-8a2f-2c59e53ae4c3',
             slug='astana', price_uid='37c308db-1f17-11ee-8a38-2c59e53ae4c2'),
        City(title='Тараз', user_uid='11a53ca4-66c9-11ee-8a3b-2c59e53ae4c3',
             slug='taraz', price_uid='a5690f58-2230-11ee-8a38-2c59e53ae4c2'),
        City(title='Атырау', user_uid='8362254b-cb31-11ee-8a3c-2c59e53ae4c1',
             slug='atyrau', price_uid='9cb83a4a-edb7-11ee-8a3d-2c59e53ae4c1'),
    ]
    # City.objects.bulk_create(cities)
    # cities = City.objects.all().values_list('id', 'user_uid', 'title')

    # villages = [Village(city_id=i[0], title=i[-1], user_uid=i[1], slug=i[1]) for i in cities]
    # Village.objects.bulk_create(villages)

    stocks = [
        Stock(id=1, title='ГП', uid='234c9704-2446-11ed-8a2f-2c59e53ae4c3', address='ул.ГП'),
        Stock(id=2, title='Шымкент', uid='ef4a379c-2e67-11ed-8a2f-2c59e53ae4c3', address='ул.Шымкент'),
        Stock(id=3, title='Алматы', uid='c10ad4ab-35f9-11ed-8a2f-2c59e53ae4c3', address='ул.Алматы'),
        Stock(id=4, title='Кызылорда', uid='9bf30a33-35fe-11ed-8a2f-2c59e53ae4c3', address='ул.Кызылорда'),
        Stock(id=5, title='Астана', uid='822cb2e2-37fd-11ed-8a2f-2c59e53ae4c3', address='ул.Астана'),
        Stock(id=6, title='Атырау', uid='ab39d4e4-c49e-11ee-8a3c-2c59e53ae4c1', address='ул.Атырау'),
        Stock(id=7, title='Тараз', uid='5310feb3-64c7-11ee-8a3b-2c59e53ae4c3', address='ул.Тараз')
    ]
    # Stock.objects.bulk_create(stocks)

    cash_boxs = [
        CashBox(title='ГП', uid="695614de-17a7-11ed-8a2f-2c59e53ae4c3", stock_id=1),
        CashBox(title='Шымкент', uid="1c32c770-2e6f-11ed-8a2f-2c59e53ae4c3", stock_id=2),
        CashBox(title='Алматы', uid="d20bf82f-35f9-11ed-8a2f-2c59e53ae4c3", stock_id=3),
        CashBox(title='Кызылорда', uid="b03691ed-35fe-11ed-8a2f-2c59e53ae4c3", stock_id=4),
        CashBox(title='Астана', uid="a10b939d-37fd-11ed-8a2f-2c59e53ae4c3", stock_id=5),
        CashBox(title='Атырау', uid="f148f0ec-cb31-11ee-8a3c-2c59e53ae4c1", stock_id=6),
        CashBox(title='Тараз', uid="2d37a413-3660-11ed-8a2f-2c59e53ae4c3", stock_id=7)

    ]
    # CashBox.objects.bulk_create(cash_boxs)

    # sync_categories()
    sync_prods_list()
    # sync_dealer()
    # sync_order_histories_1c_to_crm()
    # sync_pay_doc_histories()


def get_next_id(model):
    sequence_name = f"{model._meta.db_table}_id_seq"
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT nextval('{sequence_name}')")
        row = cursor.fetchone()
    return row[0] if row else None


@app.task
def sync_categories():
    response = requests.get(config('SYNC_1C_BASE_URL') + 'leftovers',
                            auth=(config('SYNC_1C_USERNAME').encode('utf-8'), config('SYNC_1C_PWD').encode('utf-8')))
    categories = json.loads(response.content).get('products')

    categories_data = []
    unique_check = set()

    for c in categories:
        data = {
            'uid': c['CategoryUID'],
            'title': c['CategoryName'],
            'slug': c['CategoryUID']
        }
        data_tuple = (data['uid'], data['title'], data['slug'])
        if data_tuple not in unique_check:
            unique_check.add(data_tuple)
            categories_data.append(data)
    Category.objects.bulk_create([Category(**data) for data in categories_data])


def sync_prods_list():
    response = requests.get(config('SYNC_1C_BASE_URL') + 'leftovers',
                            auth=(config('SYNC_1C_USERNAME').encode('utf-8'), config('SYNC_1C_PWD').encode('utf-8')))
    products = json.loads(response.content).get('products')

    collection_id = Collection.objects.first().id
    categories = {key: value for key, value in Category.objects.all().values_list('uid', 'id')}
    stocks = Stock.objects.all().values_list('id', flat=True)
    dealer_statuses = DealerStatus.objects.all().values_list('id', flat=True)
    price_types = PriceType.objects.all().values_list('id', flat=True)
    cities = City.objects.all().values_list('id', flat=True)
    price_cities = {key: value for key, value in City.objects.all().values_list('price_uid', 'id')}

    product_create_list = []
    product_cost_price_list = []
    product_count_list = []
    product_price_list = []

    product_id = get_next_id(AsiaProduct)
    for p in products:
        for category_uid, category_id in categories.items():
            if category_uid == p['CategoryUID']:
                product_create_list.append(
                    AsiaProduct(
                        id=product_id,
                        uid=p.get('NomenclatureUID'),
                        title=p.get('NomenclatureName'),
                        category_id=category_id,
                        collection_id=collection_id)
                )
                product_cost_price_list.append(ProductCostPrice(product_id=product_id))

                product_count_list += [ProductCount(stock_id=s, product_id=product_id) for s in stocks]

                for dealer_status in dealer_statuses:
                    for price_type in price_types:
                        product_price_list.append(
                            ProductPrice(
                                price_type_id=price_type, product_id=product_id,
                                d_status_id=dealer_status
                            )
                        )
                    for city in cities:
                        product_price_list.append(
                            ProductPrice(
                                city_id=city, product_id=product_id,
                                d_status_id=dealer_status
                            )
                        )
                product_id += 1
                break

    # AsiaProduct.objects.bulk_create(product_create_list)
    # ProductCostPrice.objects.bulk_create(product_cost_price_list)
    # ProductPrice.objects.bulk_create(product_price_list)
    # ProductCount.objects.bulk_create(product_count_list)

    prod_price_list = []  # TODO: тут переделать осталось
    for p in products:
        for c in p.get('Prices'):
            for price_city_uid, price_city_id in price_cities.items():
                if price_city_uid == c['PricetypesUID']:
                    prod_price = ProductPrice.objects.filter(
                        city_id=price_city_id,
                        product_id=product_id
                    ).first()
                    amount = int(c.get('PriceAmount'))
                    prod_price.price = amount
                    prod_price_list.append(prod_price)
                    break

    ProductPrice.objects.bulk_update(prod_price_list, ['price'])


@app.task
def sync_dealer():
    response = requests.get(config('SYNC_1C_BASE_URL') + 'clients',
                            auth=(config('SYNC_1C_USERNAME').encode('utf-8'), config('SYNC_1C_PWD').encode('utf-8')))
    clients = json.loads(response.content).get('clients')

    dealer_status = DealerStatus.objects.filter(title='C').first().id
    cities = {key: value for key, value in City.objects.all().values_list('uid', 'id')}
    user_id = get_next_id(MyUser)
    user_list = []
    profile_list = []

    for c in clients:
        for city_uid, city_id in cities.items():
            if city_uid == c['CityUID']:
                user_list.append(
                    MyUser(
                        id=user_id,
                        name=c.get('Name'),
                        uid=c.get('UID'),
                        phone=c.get('Telephone'),
                        email=c.get('UID') + "@absklad.com",
                        password='absklad123',
                        pwd='absklad123',
                        status='dealer',
                        username=c.get('UID'),
                    )
                )
                profile_list.append(
                    DealerProfile(
                        user_id=user_id,
                        dealer_status=dealer_status,
                        price_city=city_id,
                    )
                )
                user_id += 1
                break

    MyUser.objects.bulk_create(user_list)
    DealerProfile.objects.bulk_create(profile_list)
    profiles = list(DealerProfile.objects.select_related('price_city').all())

    for profile in profiles:
        profile.village = profile.price_city.villages.first()
    DealerProfile.objects.bulk_update(profiles, ['village'])

    wallet_r = []
    for dealer in DealerProfile.objects.all():
        wallet_r.append(Wallet(dealer=dealer))
    Wallet.objects.bulk_create(wallet_r)


@app.task
def sync_order_histories_1c_to_crm():
    response = requests.get(config('SYNC_1C_BASE_URL') + 'GetSale',
                            auth=(config('SYNC_1C_USERNAME').encode('utf-8'), config('SYNC_1C_PWD').encode('utf-8')))
    orders = json.loads(response.content).get('orders')

    data_order_products = []
    data_orders = []

    stocks = {key: value for key, value in Stock.objects.all().values_list('uid', 'id')}
    authors = {key: value for key, value in DealerProfile.objects.all().values_list('user__uid', 'id')}

    for o in orders:
        for author_uid, author_id in authors.items():
            if author_uid == o.get('author_uid'):
                for stock_uid, stock_id in stocks.items():
                    if stock_uid == o.get('city_uid'):
                        data_orders.append(
                            {
                                'author': author_id,
                                'price': o.get('total_price'),
                                'type_status': o.get('type_status') if o.get('type_status') else 'Карта',
                                'created_at': datetime.datetime.strptime(o.get('created_at'), "%d.%m.%Y %H:%M:%S"),
                                'released_at': datetime.datetime.strptime(o.get('created_at'), "%d.%m.%Y %H:%M:%S"),
                                'paid_at': datetime.datetime.strptime(o.get('created_at'), "%d.%m.%Y %H:%M:%S"),
                                'uid': o.get('uid'),
                                'status': 'success',
                                'stock': stock_id,
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
                        break
                break

    MyOrder.objects.bulk_create([MyOrder(**i) for i in data_orders])

    my_orders = {key: value for key, value in MyOrder.objects.all().values_list('uid', 'id')}
    asia_products = {key: value for key, value in AsiaProduct.objects.all().values_list('uid', 'id')}
    res_data = []
    for o in data_order_products:
        for order_uid, order_id in my_orders.items():
            if order_uid == o['order']:
                for product_uid, product_id in asia_products.items():
                    if product_uid == o['uid']:
                        res_data.append(
                            {
                                'order': order_id,
                                'total_price': o.get('total_price') if o.get('total_price') else 0,
                                'count': o.get('count') if o.get('count') else 0,
                                'price': o.get('price') if o.get('price') else 0,
                                'ab_product': product_id,
                            }
                        )
                        break
                break

    OrderProduct.objects.bulk_create([OrderProduct(**i) for i in res_data])

    my_orders = {key: value for key, value in MyOrder.objects.all().values_list('uid', 'id')}
    order_update_list = []

    for order_uid, order_id in my_orders.items():
        for o in orders:
            if order_uid == o['uid']:
                created_at = datetime.datetime.strptime(o.get('created_at'), "%d.%m.%Y %H:%M:%S")
                order_update_list.append(MyOrder(id=order_id, created_at=created_at))
                break

    MyOrder.objects.bulk_update(order_update_list, ['created_at'])


def sync_pay_doc_histories():
    response = requests.get(config('SYNC_1C_BASE_URL') + 'GetPyments',
                            auth=(config('SYNC_1C_USERNAME').encode('utf-8'), config('SYNC_1C_PWD').encode('utf-8')))
    payments = json.loads(response.content).get('pyments')

    users = {key: value for key, value in MyUser.objects.all().values_list('uid', 'id')}
    cash_boxs = {key: value for key, value in MyUser.objects.all().values_list('uid', 'id')}
    data_payment = []

    for p in payments:
        for user_uid, user_id in users.items():
            if user_uid == p['user_uid']:
                for cash_box_uid, cash_box_id in cash_boxs.items():
                    if cash_box_uid == p['cashbox_uid']:
                        data_payment.append(MoneyDoc(
                            status=p['order_type'],
                            user=user_id,
                            amount=p['amount'],
                            cash_box=cash_box_id,
                            uid=p['uid'],
                        ))
                        break
                break
    MoneyDoc.objects.bulk_create(data_payment)

    my_orders = {key: value for key, value in MoneyDoc.objects.all().values_list('uid', 'id')}
    update_list = []

    for order_uid, order_id in my_orders.items():
        for p in payments:
            if order_uid == p['uid']:
                created_at = datetime.datetime.strptime(p.get('created_at'), "%d.%m.%Y %H:%M:%S")
                update_list.append(MoneyDoc(id=order_id, created_at=created_at))
                break

    MoneyDoc.objects.bulk_update(update_list, ['created_at'])
