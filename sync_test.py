import datetime
import json

from django.utils import timezone

import requests
from order.models import MyOrder


def sync_test():
    a = MyOrder.objects.last().created_at
    a = {timezone.localtime(a) + datetime.timedelta(hours=6)}
    print(a)
    data = json.dumps({'uid': 'd4c3a57d-bfa4-11ee-8a3c-2c59e53ae4c1',
        'user_uid': '00000000-0000-0000-0000-000000000000',
        'delete': 1,
        'created_at': f'{a}',
       'cityUID': '822cb2e2-37fd-11ed-8a2f-2c59e53ae4c3',
        'products': [
                {'prod_uid': '926d5ec0-1c79-11ed-8a2f-2c59e53ae4c3', 'count': 1},
                {'prod_uid': 'c575c901-1c79-11ed-8a2f-2c59e53ae4c3', 'count': 1},
                {'prod_uid': 'dc16d8b3-1c79-11ed-8a2f-2c59e53ae4c3', 'count': 1},
                {'prod_uid': 'f9fdcb32-1c79-11ed-8a2f-2c59e53ae4c3', 'count': 1},
                {'prod_uid': '86900256-1c7f-11ed-8a2f-2c59e53ae4c3', 'count': 1},
                {'prod_uid': 'ed9ad307-1c80-11ed-8a2f-2c59e53ae4c3', 'count': 1},
                {'prod_uid': '190d797c-1c86-11ed-8a2f-2c59e53ae4c3', 'count': 2},
                {'prod_uid': '250c237e-1c86-11ed-8a2f-2c59e53ae4c3', 'count': 2},
                {'prod_uid': '2dfcc1c2-1c86-11ed-8a2f-2c59e53ae4c3', 'count': 1},
                {'prod_uid': '2dfcc1c3-1c86-11ed-8a2f-2c59e53ae4c3', 'count': 2},
                {'prod_uid': '831a4f42-1c86-11ed-8a2f-2c59e53ae4c3', 'count': 6},
                {'prod_uid': 'c8a69c5f-1c86-11ed-8a2f-2c59e53ae4c3', 'count': 12},
                {'prod_uid': '82ba3338-1c89-11ed-8a2f-2c59e53ae4c3', 'count': 10},
                {'prod_uid': 'aa6d1a1e-1c89-11ed-8a2f-2c59e53ae4c3', 'count': 9},
                {'prod_uid': '5eb7183b-1c8a-11ed-8a2f-2c59e53ae4c3', 'count': 1},
                {'prod_uid': '01aa4ca7-1c8e-11ed-8a2f-2c59e53ae4c3', 'count': 5},
                {'prod_uid': '4222c80d-1c8e-11ed-8a2f-2c59e53ae4c3', 'count': 9},
                {'prod_uid': 'b068d7b6-2454-11ed-8a2f-2c59e53ae4c3', 'count': 22},
                {'prod_uid': 'afd5c3e2-245f-11ed-8a2f-2c59e53ae4c3', 'count': 10},
                {'prod_uid': '416805d8-246a-11ed-8a2f-2c59e53ae4c3', 'count': 3},
                {'prod_uid': '33e78cf7-4078-11ed-8a2f-2c59e53ae4c3', 'count': 2},
                {'prod_uid': '4030bc93-4164-11ed-8a2f-2c59e53ae4c3', 'count': 10},
                  {'prod_uid': 'a829c4d4-46cb-11ed-8a30-2c59e53ae4c2', 'count': 3},
                  {'prod_uid': '38526a9a-60fa-11ed-8a30-2c59e53ae4c2', 'count': 28},
                  {'prod_uid': '96d7befb-60fa-11ed-8a30-2c59e53ae4c2', 'count': 1},
                  {'prod_uid': '70fd92f7-66f1-11ed-8a30-2c59e53ae4c2', 'count': 10},
                  {'prod_uid': '83fe07bd-717f-11ed-8a30-2c59e53ae4c2', 'count': 27},
                  {'prod_uid': '59c0fd42-7f50-11ed-8a30-2c59e53ae4c2', 'count': 29},
                  {'prod_uid': '2372074f-8660-11ed-8a30-2c59e53ae4c2', 'count': 15},
                  {'prod_uid': 'ae1eaa10-af74-11ed-8a30-2c59e53ae4c2', 'count': 18},
                  {'prod_uid': '23d255da-b8ce-11ed-8a30-2c59e53ae4c2', 'count': 2},
                  {'prod_uid': 'f3b298c8-b8da-11ed-8a30-2c59e53ae4c2', 'count': 2},
                  {'prod_uid': 'b5a0b7a0-ba8b-11ed-8a30-2c59e53ae4c2', 'count': 3},
                  {'prod_uid': '1543bcaf-ba8c-11ed-8a30-2c59e53ae4c2', 'count': 3},
                  {'prod_uid': '2f8caecc-db52-11ed-8a31-2c59e53ae4c3', 'count': 22},
                  {'prod_uid': '221a05f8-0680-11ee-8a35-2c59e53ae4c3', 'count': 1},
                  {'prod_uid': '49ea203f-0691-11ee-8a35-2c59e53ae4c3', 'count': 3},
                  {'prod_uid': '0a8446af-196c-11ee-8a36-2c59e53ae4c3', 'count': 15},
                  {'prod_uid': '2261088c-1d6c-11ee-8a38-2c59e53ae4c2', 'count': 4},
                  {'prod_uid': 'c653858f-3b66-11ee-8a39-2c59e53ae4c3', 'count': 8},
                  {'prod_uid': '6c039b7b-3c00-11ee-8a39-2c59e53ae4c3', 'count': 14},
                  {'prod_uid': 'a04da187-3c00-11ee-8a39-2c59e53ae4c3', 'count': 4},
                  {'prod_uid': '771fde5a-3c14-11ee-8a39-2c59e53ae4c3', 'count': 7},
                  {'prod_uid': '863f0e9b-47e3-11ee-8a3a-2c59e53ae4c3', 'count': 3},
                  {'prod_uid': '67fba01a-4d3f-11ee-8a3a-2c59e53ae4c3', 'count': 7},
                  {'prod_uid': 'a82e9c8c-5239-11ee-8a3a-2c59e53ae4c3', 'count': 10},
                  {'prod_uid': '855573c4-5ecc-11ee-8a3b-2c59e53ae4c3', 'count': 10},
                  {'prod_uid': '59848fef-5f48-11ee-8a3b-2c59e53ae4c3', 'count': 9},
                  {'prod_uid': '5cf83cc7-63f9-11ee-8a3b-2c59e53ae4c3', 'count': 6}]})
    print(data)
    url = 'http://91.211.251.134/testcrm/hs/asoi/CreateInventory'
    username = 'Директор'
    password = '757520ля***'
    response = requests.request("POST", url, data=data, auth=(username.encode('utf-8'), password.encode('utf-8')))
    print(response)
    print('return - ', response.text)




