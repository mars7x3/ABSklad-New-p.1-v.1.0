import datetime
import json

import requests
from django.db.models import Case, F, When, IntegerField, Value, Sum, Subquery

from absklad_commerce.celery import app
from account.models import MyUser, Wallet
from order.models import OrderProduct
from product.models import ProductCount, AsiaProduct


@app.task
def sync_balance_1c_to_crm():
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
                When(dealer__main_orders__status='paid', dealer__main_orders__is_active=True,
                     then=F('dealer__main_orders__price')),
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


@app.task
def sync_product_count():
    url = 'http://91.211.251.134/testcrm/hs/asoi/leftovers'
    username = 'Директор'
    password = '757520ля***'
    response = requests.get(url, auth=(username.encode('utf-8'), password.encode('utf-8')))
    data = json.loads(response.content)

    products_data = data.get('products')
    start_time = datetime.datetime.now()

    converted_data_map = {
        product_data["NomenclatureUID"]: {
            wh_data["WarehouseUID"]: wh_data['NomenclatureAmount']
            for wh_data in product_data['WarehousesCount']
        }
        for product_data in products_data
    }

    product_counts = (
        ProductCount.objects
        .select_related('product', 'stock')
        .filter(product__uid__in=converted_data_map.keys())
    )

    order_counts = (
        OrderProduct.objects
        .filter(
            order__stock__isnull=False,
            order__is_active=True,
            order__status="paid",
            ab_product_id__in=Subquery(product_counts.values("product_id"))
        )
        .values(product_uid=F("ab_product__uid"))
        .annotate(
            wh_uid=F("order__stock__uid"),
            count_amount=Sum("count")
        )
    )

    converted_order_counts = {}
    for count_data in order_counts:
        product_uid, wh_uid, count = count_data["product_uid"], count_data["wh_uid"], count_data["count_amount"]

        if product_uid not in converted_order_counts:
            converted_order_counts[product_uid] = {}

        converted_order_counts[product_uid][wh_uid] = count

    updated_warehouses = []
    for product_count in product_counts.distinct():
        product_uid, wh_uid = product_count.product.uid, product_count.stock.uid

        count_1c = converted_data_map.get(product_uid, {}).get(wh_uid, 0)
        product_count.count_1c = count_1c

        count_order = converted_order_counts.get(product_uid, {}).get(wh_uid, 0)
        product_count.count_order = count_order

        count_crm = count_1c - count_order if count_1c >= count_order else 0
        product_count.count_crm = count_crm

        updated_warehouses.append(product_count)

    ProductCount.objects.bulk_update(updated_warehouses, fields=['count_1c', 'count_order', 'count_crm'])

    end_time = datetime.datetime.now()



