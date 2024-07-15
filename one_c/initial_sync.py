import datetime
import json

import requests
from decouple import config
from django.db import connection, transaction

from absklad_commerce.celery import app
from account.models import DealerStatus, MyUser, DealerProfile, Wallet, ManagerProfile, WarehouseProfile, RopProfile
from chat.utils import create_chats_for_dealers
from crm_general.models import Inventory, InventoryProduct
from general_service.models import Stock, PriceType, City, CashBox, Village
from one_c.models import MoneyDoc, MovementProduct1C, MovementProducts
from order.models import MyOrder, OrderProduct
from product.models import Collection, AsiaProduct, Category, ProductCostPrice, ProductCount, ProductPrice


"""
http://91.211.251.134/testcrm/hs/asoi/CreateInventory get метод получение всех списков инвентаризаций
http://91.211.251.134/testcrm/hs/asoi/movements get получения перемещений
"""


def update_sequence(model):
    sequence_name = f"{model._meta.db_table}_id_seq"
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT MAX(id) FROM {model._meta.db_table}")
        max_id = cursor.fetchone()[0]
        cursor.execute(f"SELECT setval('{sequence_name}', %s)", [max_id])


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
                    for city_uid, city_id in price_cities.items():
                        is_create = False
                        for c in p.get('Prices'):
                            if city_uid == c['PricetypesUID']:
                                amount = int(c.get('PriceAmount'))
                                product_price_list.append(
                                    ProductPrice(
                                        city_id=city_id, product_id=product_id,
                                        d_status_id=dealer_status, price=amount
                                    )
                                )
                                is_create = True
                                break
                        if not is_create:
                            product_price_list.append(
                                ProductPrice(
                                    city_id=city_id, product_id=product_id,
                                    d_status_id=dealer_status
                                )
                            )
                product_id += 1
                break

    AsiaProduct.objects.bulk_create(product_create_list)
    ProductCostPrice.objects.bulk_create(product_cost_price_list)
    ProductPrice.objects.bulk_create(product_price_list)
    ProductCount.objects.bulk_create(product_count_list)
    update_sequence(AsiaProduct)


@app.task
def sync_dealer():
    response = requests.get(config('SYNC_1C_BASE_URL') + 'clients',
                            auth=(config('SYNC_1C_USERNAME').encode('utf-8'), config('SYNC_1C_PWD').encode('utf-8')))
    clients = json.loads(response.content).get('clients')

    dealer_status = DealerStatus.objects.filter(title='C').first().id
    cities = {key: value for key, value in City.objects.all().values_list('user_uid', 'id')}
    managers = {key: value for key, value in ManagerProfile.objects.all().values_list('city_id', 'user_id',)}
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
                        email=str(user_id) + "@absklad.com",
                        password='absklad123',
                        pwd='absklad123',
                        status='dealer',
                        username=str(user_id),
                    )
                )
                profile_list.append(
                    DealerProfile(
                        user_id=user_id,
                        dealer_status_id=dealer_status,
                        price_city_id=city_id,
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
    update_sequence(MyUser)


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
                                'author_id': author_id,
                                'price': o.get('total_price'),
                                'type_status': o.get('type_status') if o.get('type_status') else 'Карта',
                                'created_at': datetime.datetime.strptime(o.get('created_at'), "%d.%m.%Y %H:%M:%S"),
                                'released_at': datetime.datetime.strptime(o.get('created_at'), "%d.%m.%Y %H:%M:%S"),
                                'paid_at': datetime.datetime.strptime(o.get('created_at'), "%d.%m.%Y %H:%M:%S"),
                                'uid': o.get('uid'),
                                'status': 'success',
                                'stock_id': stock_id,
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
                            OrderProduct(
                                order_id=order_id,
                                total_price=o.get('total_price') if o.get('total_price') else 0,
                                count=o.get('count') if o.get('count') else 0,
                                price=o.get('price') if o.get('price') else 0,
                                ab_product_id=product_id,
                            )
                        )
                        break
                break

    OrderProduct.objects.bulk_create(res_data)

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
    response = requests.get(config('SYNC_1C_BASE_URL') + 'GetPyments', timeout=30,
                            auth=(config('SYNC_1C_USERNAME').encode('utf-8'), config('SYNC_1C_PWD').encode('utf-8')))
    payments = json.loads(response.content).get('pyments')

    users = {key: value for key, value in MyUser.objects.all().values_list('uid', 'id')}
    cash_boxs = {key: value for key, value in CashBox.objects.all().values_list('uid', 'id')}
    data_payment = []

    for p in payments:
        for user_uid, user_id in users.items():
            if user_uid == p['user_uid']:
                for cash_box_uid, cash_box_id in cash_boxs.items():
                    if cash_box_uid == p['cashbox_uid']:
                        data_payment.append(MoneyDoc(
                            status=p['order_type'],
                            user_id=user_id,
                            amount=p['amount'],
                            cash_box_id=cash_box_id,
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


def managers_create():
    user_id = get_next_id(MyUser)
    manager_profiles = []
    managers_list = []

    for city in City.objects.all().values_list('id', 'slug', 'title'):
        managers_list.append(
            MyUser(
                id=user_id,
                status='manager',
                username='mngr_' + city[1],
                email='mngr_' + city[1] + '@absklad.com',
                pwd='absklad123',
                password='absklad123',
                name='Менеджер ' + city[-1]
            )
        )

        manager_profiles.append(
            ManagerProfile(user_id=user_id, is_main=True, city_id=city[0])
        )
        user_id += 1

    MyUser.objects.bulk_create(managers_list)
    ManagerProfile.objects.bulk_create(manager_profiles)
    for manager in MyUser.objects.filter(status='manager'):
        manager.set_password('absklad123')
        manager.save()
    update_sequence(MyUser)


def rop_create():
    cities = City.objects.all().values_list('id', flat=True)
    managers = ManagerProfile.objects.all().values_list('id', flat=True)

    user = MyUser.objects.create_user(
        status='rop',
        username='rop',
        email='rop@absklad.com',
        pwd='absklad123',
        password='absklad123',
        name='РОП')
    user.set_password('absklad123')
    user.save()

    rop = RopProfile.objects.create(user=user)
    rop.cities.set(cities)
    rop.managers.set(managers)


def dealer_mng_join():
    managers = {key: value for key, value in ManagerProfile.objects.all().values_list('city__id', 'user_id')}
    for d in DealerProfile.objects.all():
        mngr_list = [managers[d.village.city.id]]
        d.managers.set(mngr_list)


def warehouses_create():
    user_id = get_next_id(MyUser)
    warehouse_profiles = []
    warehouse_list = []

    for stock in Stock.objects.all().values_list('id', 'city__slug', 'title'):
        warehouse_list.append(
            MyUser(
                id=user_id,
                status='warehouse',
                username='zvs_' + stock[1],
                email='zvs_' + stock[1] + '@absklad.com',
                pwd='absklad123',
                password='absklad123',
                name='Зав Склад ' + stock[-1]
            )
        )
        warehouse_profiles.append(
            WarehouseProfile(user_id=user_id, is_main=True, stock_id=stock[0])
        )
        user_id += 1

    MyUser.objects.bulk_create(warehouse_list)
    WarehouseProfile.objects.bulk_create(warehouse_profiles)
    update_list = []
    for warehouse in MyUser.objects.filter(status='warehouse'):
        warehouse.set_password('absklad123')
        update_list.append(warehouse)
    MyUser.objects.bulk_update(update_list, ['password'])

    update_sequence(MyUser)


def cities_create():
    cities = [
        City(title='ГП', user_uid='dc448280-350e-11ee-8a39-2c59e53ae4c3',
             slug='gp', price_uid='37bb3aee-3d5c-11ed-8a2f-2c59e53ae4c3'),
        City(title='Шымкент', user_uid='a7732ddf-2e71-11ed-8a2f-2c59e53ae4c3',
             slug='shymkent', price_uid='37c308db-1f17-11ee-8a38-2c59e53ae4c2'),
        City(title='Алматы', user_uid='1c114565-9b0d-11ed-8a30-2c59e53ae4c2',
             slug='almaty', price_uid='f16eb774-1f15-11ee-8a38-2c59e53ae4c2'),
        City(title='Кызылорда', user_uid='215eba93-3407-11ed-8a2f-2c59e53ae4c3',
             slug='kyzylorda', price_uid='07d8ff4c-1f17-11ee-8a38-2c59e53ae4c2'),
        City(title='Астана', user_uid='7400e4a9-37fc-11ed-8a2f-2c59e53ae4c3',
             slug='astana', price_uid='46a70327-1f17-11ee-8a38-2c59e53ae4c2'),
        City(title='Атырау', user_uid='8362254b-cb31-11ee-8a3c-2c59e53ae4c1',
             slug='atyrau', price_uid='9cb83a4a-edb7-11ee-8a3d-2c59e53ae4c1'),
        City(title='Тараз', user_uid='11a53ca4-66c9-11ee-8a3b-2c59e53ae4c3',
             slug='taraz', price_uid='a5690f58-2230-11ee-8a38-2c59e53ae4c2'),

    ]
    City.objects.bulk_create(cities)
    cities = City.objects.all().values_list('id', 'user_uid', 'title')

    villages = [Village(city_id=i[0], title=i[-1], user_uid=i[1], slug=i[1]) for i in cities]
    Village.objects.bulk_create(villages)


def collections_create():
    Collection.objects.create(title='ASIABRAND', slug='asiabrand')


def dealer_statuses_create():
    DealerStatus.objects.create(title='C', is_active=True)


def stocks_create():
    stocks = [
        Stock(id=1, city_id=1, title='ГП', uid='234c9704-2446-11ed-8a2f-2c59e53ae4c3', address='ул.ГП',
              shedule='Работаем 24/7'),
        Stock(id=2, city_id=2, title='Шымкент', uid='ef4a379c-2e67-11ed-8a2f-2c59e53ae4c3', address='ул.Шымкент',
              shedule='Работаем 24/7'),
        Stock(id=3, city_id=3, title='Алматы', uid='c10ad4ab-35f9-11ed-8a2f-2c59e53ae4c3', address='ул.Алматы',
              shedule='Работаем 24/7'),
        Stock(id=4, city_id=4, title='Кызылорда', uid='9bf30a33-35fe-11ed-8a2f-2c59e53ae4c3', address='ул.Кызылорда',
              shedule='Работаем 24/7'),
        Stock(id=5, city_id=5, title='Астана', uid='822cb2e2-37fd-11ed-8a2f-2c59e53ae4c3', address='ул.Астана',
              shedule='Работаем 24/7'),
        Stock(id=6, city_id=6, title='Атырау', uid='ab39d4e4-c49e-11ee-8a3c-2c59e53ae4c1', address='ул.Атырау',
              shedule='Работаем 24/7'),
        Stock(id=7, city_id=7, title='Тараз', uid='5310feb3-64c7-11ee-8a3b-2c59e53ae4c3', address='ул.Тараз',
              shedule='Работаем 24/7')
    ]
    Stock.objects.bulk_create(stocks)


def cash_boxs_create():
    cash_boxs = [
        CashBox(title='ГП', uid="695614de-17a7-11ed-8a2f-2c59e53ae4c3", stock_id=1),
        CashBox(title='Шымкент', uid="1c32c770-2e6f-11ed-8a2f-2c59e53ae4c3", stock_id=2),
        CashBox(title='Алматы', uid="d20bf82f-35f9-11ed-8a2f-2c59e53ae4c3", stock_id=3),
        CashBox(title='Кызылорда', uid="b03691ed-35fe-11ed-8a2f-2c59e53ae4c3", stock_id=4),
        CashBox(title='Астана', uid="a10b939d-37fd-11ed-8a2f-2c59e53ae4c3", stock_id=5),
        CashBox(title='Атырау', uid="f148f0ec-cb31-11ee-8a3c-2c59e53ae4c1", stock_id=6),
        CashBox(title='Тараз', uid="2d37a413-3660-11ed-8a2f-2c59e53ae4c3", stock_id=7)

    ]
    CashBox.objects.bulk_create(cash_boxs)


def sync_movement_history():
    response = requests.get(config('SYNC_1C_BASE_URL') + 'movements',
                            auth=(config('SYNC_1C_USERNAME').encode('utf-8'), config('SYNC_1C_PWD').encode('utf-8')))
    movements = json.loads(response.content).get('movements')
    stocks = {key: value for key, value in Stock.objects.all().values_list('uid', 'id')}
    products = {key: value for key, value in AsiaProduct.objects.all().values_list('uid', 'id')}

    next_id = 1
    movements_list = []
    products_list = []

    for movement in movements:
        sender_id = stocks.get(movement['warehouse_sender_uid'], None)
        recipient_id = stocks.get(movement['warehouse_recipient_uid'], None)
        if recipient_id or sender_id:
            movements_list.append(
                MovementProduct1C(
                    id=next_id,
                    warehouse_sender_id=sender_id,
                    warehouse_recipient_id=recipient_id,
                    uid=movement['journey_uid'],
                    created_at=datetime.datetime.strptime(movement['created_at'], "%d.%m.%Y %H:%M:%S")
                )
            )

            for p in movement['products']:
                for p_uid, p_id in products.items():
                    if p_uid == p['prod_uid']:
                        products_list.append(MovementProducts(movement_id=next_id, product_id=p_id, count=p['count']))
            next_id += 1

    MovementProduct1C.objects.bulk_create(movements_list)
    MovementProducts.objects.bulk_create(products_list)


def other_employees():
    user = MyUser.objects.create_user(
        status='director',
        username='director',
        email='director@absklad.com',
        pwd='absklad123',
        password='absklad123',
        name='Director')
    user.set_password('absklad123')
    user.save()

    user = MyUser.objects.create_user(
        status='accountant',
        username='accountant',
        email='accountant@absklad.com',
        pwd='absklad123',
        password='absklad123',
        name='Accountant')
    user.set_password('absklad123')
    user.save()

    user = MyUser.objects.create_user(
        status='marketer',
        username='marketer',
        email='marketer@absklad.com',
        pwd='absklad123',
        password='absklad123',
        name='Marketer')
    user.set_password('absklad123')
    user.save()


def main_initial_sync():
    collections_create()
    dealer_statuses_create()
    cities_create()
    stocks_create()
    cash_boxs_create()

    other_employees()
    rop_create()
    managers_create()
    warehouses_create()

    sync_categories()
    sync_prods_list()
    sync_dealer()
    dealer_mng_join()
    create_chats_for_dealers(user_ids=MyUser.objects.all().values_list("id", flat=True))
    sync_order_histories_1c_to_crm()
    sync_pay_doc_histories()
    sync_movement_history()
    # Добавить инвентаризацию


