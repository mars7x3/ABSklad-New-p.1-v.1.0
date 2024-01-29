import datetime
import json

import requests
from django.db.models import Case, F, When, IntegerField, Value, Sum

from absklad_commerce.celery import app
from account.models import MyUser, Wallet
from order.models import OrderProduct
from product.models import ProductCount


@app.task
def sync_balance_1c_to_crm():
    print('***sync_balance_1c_to_crm***')
    url = "http://91.211.251.134/testcrm/hs/asoi/Balance"
    username = 'Директор'
    password = '757520ля***'
    response = requests.request("GET", url, auth=(username.encode('utf-8'), password.encode('utf-8')))
    response_data = json.loads(response.content)
    response_wallets = response_data.get('wallets')
    a = datetime.datetime.now()
    users_uid = {uid['user_uid']: uid['amount'] for uid in response_wallets}

    cases = [When(dealer__user__uid=user_uid, then=Value(amount, output_field=IntegerField())) for user_uid, amount in
             users_uid.items()]

    annotated_wallets = Wallet.objects.filter(
        dealer__user__uid__in=users_uid.keys()
    ).annotate(
        amount_1c_new=Case(*cases, default=F('amount_1c'), output_field=IntegerField()),
        amount_paid=Sum(
            Case(
                When(dealer__orders__status='paid', dealer__orders__is_active=True,
                     then=F('dealer__orders__price')),
                default=0,
                output_field=IntegerField()
            )
        )
    )

    update_data = [
        {'id': wallet.id,
         'amount_1c': wallet.amount_1c_new,
         'amount_crm': wallet.amount_1c_new - wallet.amount_paid,
         } for wallet in annotated_wallets
    ]

    Wallet.objects.bulk_update([Wallet(**data) for data in update_data], ['amount_1c', 'amount_crm'])
    b = datetime.datetime.now() - a
    print(b)


@app.task
def sync_product_count():
    print("***START SYNC PRODUCT COUNT***")
    url = 'http://91.211.251.134/testcrm/hs/asoi/leftovers'
    username = 'Директор'
    password = '757520ля***'
    response = requests.get(url, auth=(username.encode('utf-8'), password.encode('utf-8')))
    data = json.loads(response.content)

    products_data = data.get('products')
    start_time = datetime.datetime.now()

    converted_data_map = {
        product_data['NomenclatureUID']: {
            wh_data['WarehouseUID']: wh_data['NomenclatureAmount']
            for wh_data in product_data['WarehousesCount']
        }
        for product_data in products_data
    }

    product_counts = ProductCount.objects.select_related('product', 'stock')

    updated_warehouses = []
    for product_count in product_counts:
        product_uid = product_count.product.uid
        wh_uid = product_count.stock.uid
        product_count.count = converted_data_map.get(product_uid, {}).get(wh_uid, 0)
        updated_warehouses.append(product_count)

    ProductCount.objects.bulk_update(updated_warehouses, fields=['count_1c'])

    end_time = datetime.datetime.now()
    print("***END SYNC PRODUCT COUNT***", end_time - start_time)


