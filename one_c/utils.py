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
from crm_general.models import Inventory, InventoryProduct
from crm_kpi.utils import update_dealer_kpi_by_order
from crm_stat.tasks import main_stat_order_sync, main_stat_pds_sync
from general_service.models import Stock, City, PriceType, CashBox
from one_c.models import MoneyDoc, MovementProduct1C, MovementProducts
from order.models import MyOrder, OrderProduct, ReturnOrder, ReturnOrderProduct
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
        product = AsiaProduct.objects.filter(uid=p.get('uid')).first()
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


def sync_prod_crud_1c_crm(data):  # sync product 1C -> CRM
    if data.get('products'):
        return

    print('***Product CRUD***')
    print(data)
    dealer_statuses = DealerStatus.objects.all()
    cities = City.objects.all()
    p_types = PriceType.objects.all()

    price_create = []
    uid = data.get('product_uid')
    product = AsiaProduct.objects.filter(uid=uid).first()
    if product:
        category = Category.objects.filter(uid=data.get('category_uid'))
        if category:
            product.category = category.first()

        product.title = data.get('title')
        product.is_active = not bool(data.get('delete'))
        product.vendor_code = data.get('vendor_code')
        product.save()

    else:
        product = AsiaProduct.objects.create(uid=uid, title=data.get('title'),
                                             is_active=not bool(data.get('delete')),
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


def sync_1c_money_doc_crud(data):
    money_doc = MoneyDoc.objects.filter(uid=data.get('doc_uid')).first()
    user = MyUser.objects.filter(uid=data.get('user_uid')).first()
    cash_box = CashBox.objects.filter(uid=data.get('kassa')).first()

    if not user:
        print('Контрагент не существует')
        return False, 'Контрагент не существует'
    if not cash_box and data.get('doc_type') != 'Без нал':
        print('Касса не существует')
        return False, 'Касса не существует'
    if money_doc:
        is_check = False
        if bool(data.get('delete')) == money_doc.is_active:
            is_check = True

        money_doc.status = data.get('doc_type')
        money_doc.is_active = not bool(data.get('delete'))
        money_doc.amount = data.get('amount')
        money_doc.created_at = datetime.datetime.strptime(data.get('created_at'), '%Y-%m-%dT%H:%M:%S')
        money_doc.save()

        if is_check:
            money_doc.is_checked = False
            money_doc.save()
            print('Check stat')
            main_stat_pds_sync(money_doc)
            print('End Check stat')
            money_doc.is_checked = True
            money_doc.save()
            print(money_doc.is_checked)

    else:
        data = {
            'uid': data.get('doc_uid'),
            'user': user,
            'cash_box': cash_box,
            'status': data.get('doc_type'),
            'is_active': not bool(data.get('delete')),
            'amount': data.get('amount'),
            'created_at': datetime.datetime.strptime(data.get('created_at'), '%Y-%m-%dT%H:%M:%S')
        }
        money_doc = MoneyDoc.objects.create(**data)
        print('Check stat')
        main_stat_pds_sync(money_doc)
        print('End Check stat')
        money_doc.is_checked = True
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
        'is_active': not bool(request.data.get('delete'))
    }
    d_status = DealerStatus.objects.filter(discount=0).first()

    profile_data = {
        "liability": request.data.get('Liability'),
        "address": request.data.get("Address"),
        "dealer_status": d_status
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
        data['is_active'] = False
        user = MyUser.objects.create_user(**data)
        profile = DealerProfile.objects.create(user=user, **profile_data)

    Wallet.objects.get_or_create(dealer=profile)


def sync_category_1c_to_crm(data):
    category = Category.objects.filter(uid=data.get('category_uid')).first()
    if category:
        category.title = data.get('category_title')
        category.is_active = not bool(data.get('delete'))
        category.save()
    else:
        Category.objects.create(title=data.get('category_title'), uid=data.get('category_uid'),
                                slug=data.get('category_uid'), is_active=not bool(data.get('delete')))


def order_1c_to_crm(data):
    order_data = dict()
    products = data.get('products')
    user = MyUser.objects.filter(uid=data.get('user_uid')).first()
    city_stock = Stock.objects.filter(uid=data.get('cityUID')).first()

    if user and city_stock:
        order_data['author'] = user.dealer_profile
        order_data['cost_price'] = total_cost_price(products)
        order_data['status'] = 'sent'
        order_data['uid'] = data.get('order_uid')
        order_data['price'] = data.get('total_price')
        order_data['type_status'] = 'wallet'
        order_data['stock'] = city_stock
        order_data['created_at'] = datetime.datetime.strptime(data.get('created_at'), "%d.%m.%Y %H:%M:%S")
        order_data['released_at'] = datetime.datetime.strptime(data.get('created_at'), "%d.%m.%Y %H:%M:%S")
        order_data['paid_at'] = datetime.datetime.strptime(data.get('created_at'), "%d.%m.%Y %H:%M:%S")
        order_data['is_active'] = not bool(data['delete'])

        order = MyOrder.objects.filter(uid=data.get("order_uid")).first()
        if order:
            # update
            order_data.pop('paid_at')
            order_data.pop('created_at')
            is_check = False
            if order.is_active == bool(data['delete']):
                is_check = True

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

            if is_check:
                update_data = []
                for p in order.order_products.all():
                    p.is_checked = False
                    update_data.append(p)
                OrderProduct.objects.bulk_update(update_data, ['is_checked'])
                print("START Check")
                main_stat_order_sync(order)
                print("END Check")

                update_data = []
                for p in order.order_products.all():
                    p.is_checked = True
                    update_data.append(p)
                OrderProduct.objects.bulk_update(update_data, ['is_checked'])

                for i in order.order_products.all():
                    print(i.is_checked)

        else:
            # create order
            order = MyOrder.objects.create(**order_data)

            products_data = generate_products_data(products)
            OrderProduct.objects.bulk_create([OrderProduct(order=order, **i) for i in products_data])
            minus_quantity(order)

            print("START Check")
            main_stat_order_sync(order)
            print("END Check")

            update_data = []
            for p in order.order_products.all():
                p.is_checked = True
                update_data.append(p)
            OrderProduct.objects.bulk_update(update_data, ['is_checked'])
            for i in order.order_products.all():
                print(i.is_checked)

            kwargs = {'user': user, 'title': f'Заказ #{order.id}', 'description': "Заказ успешно создан.",
                      'link_id': order.id, 'status': 'order', 'is_push': True}
            Notification.objects.create(**kwargs)

            # change_dealer_status.delay(user.id)


def sync_1c_price_city_crud(data):
    city = City.objects.filter(price_uid=data['uid']).first()
    price_type = PriceType.objects.filter(uid=data['uid']).first()

    if city:
        city.is_active = not bool(data['delete'])
        city.title = data['title']
        city.save()
    elif price_type:
        price_type.is_active = not bool(data['delete'])
        price_type.title = data['title']
        price_type.save()
    else:
        data = {
            'uid': data['uid'],
            'title': data['title'],
            'is_active': not bool(data['delete'])
        }
        PriceType.objects.create(**data)
    return True, 'Success!'


def sync_1c_user_city_crud(data):
    city = City.objects.filter(user_uid=data['uid']).first()
    title = translit(data['title'], 'ru', reversed=True)
    slug = title.replace(' ', '_').lower()
    if city:
        city.is_active = not bool(data['delete'])
        city.title = data['title']
        city.slug = slug
        city.save()
    else:
        data = {
            'uid': data['uid'],
            'title': data['title'],
            'is_active': not bool(data['delete']),
            'slug': slug
        }
        City.objects.create(**data)
    return True, 'Success!'


def sync_1c_stock_crud(data):
    stock = Stock.objects.filter(uid=data['uid']).first()
    if stock:
        stock.is_active = not bool(data['delete'])
        stock.title = data['title']
        stock.save()
    else:
        data = {
            'uid': data['uid'],
            'title': data['title'],
            'is_active': not bool(data['delete']),
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


def sync_1c_inventory_crud(data):
    stock = Stock.objects.filter(uid=data.get('cityUID')).first()
    print(stock.title)
    if not stock:
        return False, 'Stock не найден!'
    sender = stock.warehouse_profiles.filter(user__is_active=True).first()
    print(sender)

    inventory_data = {
        'uid': 'd4c3a57d-bfa4-11ee-8a3c-2c59e53ae4c1',
        'is_active': not bool(data.get('delete')),
        'created_at': datetime.datetime.strptime(
            data.get('created_at'), "%d.%m.%Y %H:%M:%S"),
        'updated_at': datetime.datetime.strptime(
            data.get('created_at'), "%d.%m.%Y %H:%M:%S"),
        'sender_id': sender.user_id,
        'status': 'moderated',
         }

    inventory = Inventory.objects.filter(uid=data['uid']).first()
    if inventory:
        for key, value in inventory_data.items():
            setattr(inventory, key, value)
        inventory.save()

        update_data = []
        create_data = []
        for p in data['products']:
            prod = inventory.products.filter(product__uid=p['prod_uid']).first()
            if prod:
                prod.count = p['count']
                update_data.append(prod)
            else:
                product = AsiaProduct.objects.filter(uid=p['prod_uid']).first()
                if product:
                    create_data.append(
                        InventoryProduct(
                            inventory=inventory,
                            product=product,
                            count=p['count']
                        )
                    )
        InventoryProduct.objects.bulk_update(update_data, ['count'])
        InventoryProduct.objects.bulk_create(create_data)

        return True, 'Success!'
    else:
        inventory = Inventory.objects.create(**inventory_data)
        create_data = []
        for p in data['products']:
            product = AsiaProduct.objects.filter(uid=p['prod_uid']).first()
            if product:
                create_data.append(
                    InventoryProduct(
                        inventory=inventory,
                        product=product,
                        count=p['count']
                    )
                )
        InventoryProduct.objects.bulk_create(create_data)
        return True, 'Success!'


def sync_1c_movement_crud(data):
    sender_stock = Stock.objects.filter(uid=data['warehouse_sender_uid']).first()
    recipient_stock = Stock.objects.filter(uid=data['warehouse_recipient_uid']).first()
    movement_data = {
        'is_active': not bool(data['delete']),
        'uid': data['journey_uid'],
        'warehouse_recipient': recipient_stock,
        'warehouse_sender': sender_stock,
        'created_at': datetime.datetime.strptime(
            data.get('created_at'), "%d.%m.%Y %H:%M:%S"),
        'updated_at': datetime.datetime.strptime(
            data.get('created_at'), "%d.%m.%Y %H:%M:%S"),
    }
    movement = MovementProduct1C.objects.filter(uid=data['uid'])
    if movement:
        for key, value in movement_data.items():
            setattr(movement, key, value)
        movement.save()

    else:
        movement = MovementProduct1C.objects.create(**movement_data)

    result = {i['product_uid']: i['counts'] for i in data['products']}
    products = AsiaProduct.objects.filter(uid__in=result.keys()).values_list('uid', 'id')
    products = {i[0]: i[1] for i in products}
    create_data = []
    for p_uid, p_id in products.items():
        create_data.append(
            MovementProducts(
                movement=movement,
                product_id=p_id,
                count=result[p_uid]
            )
        )

    MovementProducts.objects.bulk_create(create_data)

    return True, 'Success!'


def sync_1c_return_crud(data):
    order = MyOrder.objects.filter(uid=data['uid_sale']).first()
    if not order:
        return False, 'Заказ отсутствует!'

    return_data = {
        'order': order,
        'created_at': datetime.datetime.strptime(
            data.get('created_at'), "%d.%m.%Y %H:%M:%S"),
        'uid': data['uid'],
        'is_active': not bool(data['delete'])
    }

    order_return = ReturnOrder.objects.filter(uid=data['uid']).first()
    if order_return:
        for key, value in return_data.items():
            setattr(order_return, key, value)
        order_return.save()

    else:
        order_return = ReturnOrder.objects.create(**return_data)

    result = {i['uid']: i['count'] for i in data['products_return']}
    products = AsiaProduct.objects.filter(uid__in=result.keys()).values_list('uid', 'id')
    products = {i[0]: i[1] for i in products}

    create_data = []
    for p_uid, p_id in products.items():
        create_data.append(
            ReturnOrderProduct(
                return_order=order_return,
                product_id=p_id,
                status='success',
                count=result[p_uid]
            )
        )
    order_return.products.all().delete()
    ReturnOrderProduct.objects.bulk_create(create_data)

    return True, 'Success!'

