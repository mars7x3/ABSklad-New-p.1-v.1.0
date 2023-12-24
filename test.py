import requests


# api_key = 'kz8117159b2a1da2d17a9b1dda664a5f4f54f6ada074b7c5dbdd19a85d0fcc5e0211b0'
# api_url = 'http://api.mobizon.kz/service/message/'
#
#
# def send_text():
#     # Определите параметры сообщения
#     params = {
#         'recipient': '+996550211788',
#         'text': 'Test sms message',
#         'from': 'ABSKLAD',
#         'apiKey': api_key
#     }
#
#     # Отправка SMS
#     response = requests.get(api_url + 'sendsmsmessage', params=params)
#     print(response.json())


# from account.models import MyUser, Notification
#
# a = MyUser.objects.get(username='dealer_1')
#
# Notification.objects.create(user=a, status='notif', title='Hello!',
#                             description='This is ASIA BRAND!')
# Notification.objects.create(user=a, status='chat', title='Привет! Меня зовут Марсел - твой менеджер.',
#                             description='Привет! Меня зовут Марсел - твой менеджер.')


# from general_service.models import Stock
# from product.models import AsiaProduct
#
#
# Stock.objects.filter(counts__product_id=1)


# from product.models import AsiaProduct, ProductCount, ProductPrice, ProductSize
# from general_service.models import Stock, City
# from account.models import DealerStatus
#
# products = AsiaProduct.objects.all()
# count_list = []
# price_list = []
# size_list = []
#
# for p in products:
#     stocks = Stock.objects.all()
#     size_list.append(ProductSize(product=p, title='Шкаф', length=100, width=500, height=300))
#     for s in stocks:
#         count_list.append(
#             ProductCount(
#                 product=p,
#                 stock=s,
#                 count_crm=100,
#                 count_1c=100,
#                 count_order=0
#             )
#         )
#     cities = City.objects.all()
#     for c in cities:
#         d_statuses = DealerStatus.objects.all()
#         for d in d_statuses:
#             price_list.append(
#                 ProductPrice(
#                     product=p,
#                     city=c,
#                     d_status=d,
#                     price=100000
#                 )
#             )
#
#
# ProductPrice.objects.bulk_create(price_list)
# ProductCount.objects.bulk_create(count_list)
# ProductSize.objects.bulk_create(size_list)


# from account.models import MyUser
#
# u = MyUser.objects.filter(name__icontains='Асан', status__in=['rop', 'manager', 'marketer',
#                                                               'accountant', 'warehouse', 'director'])

