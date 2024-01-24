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
from crm_kpi.utils import update_dealer_kpi_by_tx
from general_service.models import Stock, City, PriceType, CashBox
from one_c.models import MoneyDoc
from order.models import MyOrder, OrderProduct
from product.models import AsiaProduct, Category, ProductCount, ProductPrice, Collection


def sync_category_crm_to_1c(category):
    url = "http://91.211.251.134/testcrm/hs/asoi/CategoryGoodsCreate"
    payload = json.dumps({
        "NomenclatureName": '',
        "NomenclatureUID": '',
        "category_title": category.title,
        "category_uid": category.uid,
        "is_active": int(category.is_active),
        "vendor_code": '',
        "is_product": 0
    })

    username = 'Директор'
    password = '757520ля***'
    print(payload)
    response = requests.request("POST", url, data=payload, auth=(username.encode('utf-8'), password.encode('utf-8')))
    print(response.text)
    response_data = json.loads(response.content)
    uid = response_data.get('category_uid')

    category.uid = uid
    category.save()


def sync_product_crm_to_1c(product):
    url = "http://91.211.251.134/testcrm/hs/asoi/GoodsCreate"
    payload = json.dumps({
        "NomenclatureName": product.title,
        "NomenclatureUID": product.uid,
        "CategoryName": product.category.title,
        "CategoryUID": product.category.uid,
        "is_active": int(product.is_active),
        "vendor_code": product.vendor_code,
        "is_product": 1
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


def sync_dealer_back_to_1C(dealer):
    username = 'Директор'
    password = '757520ля***'
    url = "http://91.211.251.134/testcrm/hs/asoi/clients"
    profile = dealer.dealer_profile
    if not dealer.is_active:
        payload = {"uid": dealer.uid}
        print(payload)
        response = requests.request("DELETE", url, data=payload,
                                    auth=(username.encode('utf-8'), password.encode('utf-8')))
        print(response.text)
    payload = json.dumps({
        "clients": [{
            "is_active": int(dealer.is_active),
            'Name': dealer.name,
            'UID': dealer.uid,
            'Telephone': dealer.phone,
            'Address': profile.address,
            'Liability': profile.liability,
            'Email': dealer.email,
            'City': profile.village.city.title if profile.village else '',
            'CityUID': profile.village.city.user_uid if profile.village else '00000000-0000-0000-0000-000000000000',
        }]})

    print('***DEALER SYNC***')
    print(payload)
    response = requests.request("POST", url, data=payload, auth=(username.encode('utf-8'), password.encode('utf-8')))
    print(response.text)
    response_data = json.loads(response.content)

    dealer_uid = response_data.get('client')
    if dealer_uid:
        dealer.uid = dealer_uid
        dealer.save()


def sync_return_order_to_1C(returns_order):
    url = "http://91.211.251.134/testcrm/hs/asoi/ReturnGoods"
    products = returns_order.return_products.all()
    payload = json.dumps({
        "uid": returns_order.order.uid,
        "created_at": f'{timezone.localtime(returns_order.created_at) + datetime.timedelta(hours=6)}',
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


def sync_1c_money_doc(money_doc):
    url = "http://91.211.251.134/testcrm/hs/asoi/CreateaPyment"
    if money_doc.status == 'Без нал':
        cash_box_uid = ''
    else:
        city = money_doc.user.dealer_profile.village.city
        cash_box = city.stocks.first().cash_box
        cash_box_uid = cash_box.uid
    # TODO: если в регионе будет больше 1 склада, то надо будет логику кассы поменять.

    payload = json.dumps({
        "user_uid": money_doc.user.uid,
        "amount": int(money_doc.amount),
        "created_at": f'{timezone.localtime(money_doc.created_at) + datetime.timedelta(hours=6)}',
        "order_type": money_doc.status,
        "cashbox_uid": cash_box_uid,
        "is_active": int(money_doc.is_active),
        "uid": money_doc.uid
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
    update_dealer_kpi_by_tx(money_doc)


def sync_money_doc_to_1C(order):
    try:
        with transaction.atomic():
            url = "http://91.211.251.134/testcrm/hs/asoi/CreateaPyment"
            if 'cash' == order.type_status or order.type_status == 'kaspi':
                type_status = 'Наличка'
                cash_box_uid = order.stock.cash_box.uid
            else:
                type_status = 'Без нал'
                cash_box_uid = ''
            payload = json.dumps({
                "user_uid": order.author.user.uid,
                "amount": int(order.price),
                "created_at": f'{timezone.localtime(order.created_at) + datetime.timedelta(hours=6)}',
                "order_type": type_status,
                "cashbox_uid": cash_box_uid,
                "is_active": 1,
                "uid": "00000000-0000-0000-0000-000000000000"
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
            order.paid_at = timezone.now()
            order.save()
            m_d = MoneyDoc.objects.create(order=order, user=order.author.user, amount=order.price, uid=payment_doc_uid)
            update_dealer_kpi_by_tx(m_d)
    except Exception as e:
        raise TypeError


def sync_order_to_1C(order):
    try:
        with transaction.atomic():
            url = "http://91.211.251.134/testcrm/hs/asoi/CreateSale"
            products = order.order_products.all()
            released_at = timezone.localtime(order.released_at) + datetime.timedelta(hours=6)
            money = order.money_docs.filter(is_active=True).first()
            payload = json.dumps({
                "user_uid": order.author.user.uid,
                "created_at": f'{released_at}',
                "payment_doc_uid": money.uid if money else '00000000-0000-0000-0000-000000000000',
                "cityUID": order.stock.uid,
                "is_active": int(order.is_active),
                "uid": order.uid,
                "products": [
                    {"title": p.title,
                     "uid": p.ab_product.uid,
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
            order.released_at = timezone.now()
            order.save()
    except Exception as e:
        raise TypeError


def sync_stock_1c_2_crm(stock):
    url = "http://91.211.251.134/testcrm/hs/asoi/Warehouses"

    payload = json.dumps({
        "CategoryUID": stock.uid,
        "title": stock.title,
        "is_active": int(stock.is_active)
    })

    username = 'Директор'
    password = '757520ля***'
    print(payload)
    response = requests.request("POST", url, data=payload,
                                auth=(username.encode('utf-8'), password.encode('utf-8')))
    print(response.text)
    response_data = json.loads(response.content)
    uid = response_data.get('result_uid')
    stock.uid = uid
    stock.save()
