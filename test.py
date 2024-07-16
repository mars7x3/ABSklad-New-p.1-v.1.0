# import random
#
# import requests
#
# # api_key = 'kz8117159b2a1da2d17a9b1dda664a5f4f54f6ada074b7c5dbdd19a85d0fcc5e0211b0'
# # api_url = 'http://api.mobizon.kz/service/message/'
# #
# #
# # def send_text():
# #     # Определите параметры сообщения
# #     params = {
# #         'recipient': '+996550211788',
# #         'text': 'Test sms message',
# #         'from': 'ABSKLAD',
# #         'apiKey': api_key
# #     }
# #
# #     # Отправка SMS
# #     response = requests.get(api_url + 'sendsmsmessage', params=params)
# #     print(response.json())
#
#
# # from account.models import MyUser, Notification
# #
# # a = MyUser.objects.get(username='dealer_1')
# #
# # Notification.objects.create(user=a, status='notif', title='Hello!',
# #                             description='This is ASIA BRAND!')
# # Notification.objects.create(user=a, status='chat', title='Привет! Меня зовут Марсел - твой менеджер.',
# #                             description='Привет! Меня зовут Марсел - твой менеджер.')
#
#
# # from general_service.models import Stock
# # from product.models import AsiaProduct
# #
# #
# # Stock.objects.filter(counts__product_id=1)
#
#
# from product.models import AsiaProduct, ProductCount, ProductPrice, ProductSize
# from general_service.models import Stock, PriceType
# from account.models import DealerStatus
#
# # products = AsiaProduct.objects.all()
# # count_list = []
# # price_list = []
# # size_list = []
# #
# # x = 1
# # for p in products:
# #     stocks = Stock.objects.all()
# #     # size_list.append(ProductSize(product=p, title='Шкаф', length=100, width=500, height=300))
# #     for s in stocks:
# #         count_list.append(
# #             ProductCount(
# #                 product=p,
# #                 stock=s,
# #                 count_crm=100,
# #                 count_1c=100,
# #                 count_order=0,
# #                 count_norm=50
# #
# #             )
# #         )
# #     cities = PriceType.objects.all()
# #     amount = 50000 * x
# #     for c in cities:
# #         d_statuses = DealerStatus.objects.all()
# #         for d in d_statuses:
# #             price_list.append(
# #                 ProductPrice(
# #                     product=p,
# #                     price_type=c,
# #                     d_status=d,
# #                     price=amount
# #                 )
# #             )
# #     x += 1
# #
# # ProductPrice.objects.all().delete()
# # ProductCount.objects.all().delete()
# # ProductPrice.objects.bulk_create(price_list)
# # ProductCount.objects.bulk_create(count_list)
# # ProductSize.objects.bulk_create(size_list)
#
#
# # from account.models import MyUser
# #
# # u = MyUser.objects.filter(name__icontains='Асан', status__in=['rop', 'manager', 'marketer',
# #                                                               'accountant', 'warehouse', 'director'])
#
#
# from promotion.models import Motivation, ConditionProduct
# from product.models import AsiaProduct
#
# prods = AsiaProduct.objects.filter(id__in=[305, 308])
# a = Motivation.objects.get(id=32)
# for i in a.conditions.all():
#     for b in i.condition_prods.all():
#         print(b)
#         # for p in prods:
#         #     ConditionProduct.objects.create(condition=b, product=p, count=5)
#
#
# def rounding(n, m):
#     pass
#
#
# from order.models import MainOrder, MyOrder
#
# o = MainOrder.objects.get(id=64)
#
# my_o = MyOrder.objects.create(main_order=o,
#                               author=o.author,
#                               stock=o.stock,
#                               price=o.price,
#                               status='sent',
#                               type_status=o.type_status,
#                               created_at=o.created_at,
#                               paid_at=o.paid_at)
#
# from account.models import MyUser
#
# a = MyUser.objects.filter(username='azat').first()
# a.pwd
import pandas
from django.db.models import F, IntegerField, CharField, Value
from django.db.models.functions import Cast

from one_c.models import MoneyDoc
from order.models import MyOrder


def get_balance_history(user_id, start_date, end_date):
    orders = (
        MyOrder.objects.filter(
            author__user_id=user_id,
            is_active=True,
            status__in=['success', 'sent', 'wait', 'paid'],
        ).values(
            'created_at',
            action_id=F('id'),
            after=Value(0, IntegerField()),
            before=Value(0, IntegerField()),
            type=Value('order', CharField()),
            price_amount=Cast(F('price'), IntegerField(default=0)),
        )
    )
    balances = (
        MoneyDoc.objects.filter(user_id=user_id, is_active=True)
        .values(
            'created_at',
            action_id=F('id'),
            after=Value(0, IntegerField()),
            before=Value(0, IntegerField()),
            type=Value('wallet', CharField()),
            price_amount=Cast(F('price'), IntegerField(default=0)),
        )
    )

    data = list(orders) + list(balances)
    df = pandas.DataFrame(data).sort_values(by='created_at')
    balance = 0

    for index, row in df.iterrows():
        df.at[index, 'before'] = balance

        match row['type']:
            case 'wallet':
                balance += row['price_amount']
            case 'order':
                balance -= row['price_amount']

        df.at[index, 'after'] = balance

    start_date = pandas.to_datetime(start_date).tz_localize(df['created_at'].dt.tz)
    end_date = pandas.to_datetime(end_date).tz_localize(df['created_at'].dt.tz)

    df = df[(start_date <= df['created_at']) & (df['created_at'] < end_date)]
    df.rename(columns={'type': 'status', 'price_amount': 'amount'}, inplace=True)
    return df.to_dict('records')
