import datetime
import re
import pandas

import requests
import json

from django.utils.crypto import get_random_string
from decouple import config
from account.models import Notification, BalancePlus
from crm_general.models import AutoNotification
from one_c.models import MoneyDoc
from order.models import MyOrder


def random_code():
    code = get_random_string(length=4, allowed_chars='0123456789')
    return code


def send_code_to_email(email):
    pass


def send_code_to_phone(phone, text):
    api_key = 'kz4dff49ea3b3dd2237043ca1aae22a095664e726e025a8c34e822da61458c0d2620b3'
    api_url = 'https://api.mobizon.kz/service/message/sendsmsmessage'
    text = 'Ваш код для ASIABRAND: ' + text
    params = {
        'recipient': phone,
        'from': 'ASIABRAND',
        'text': text,
        'apiKey': api_key,
    }
    # Отправка SMS
    api_url = api_url + f'?recipient={phone}&text={text}&apiKey={api_key}'
    response = requests.get(api_url, params=params)


def generate_pwd() -> str:
    password = get_random_string(length=8,
                                 allowed_chars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    return password


def send_push_notification(tokens: [], title: str, text: str, link_id: int, status: str):
    url = "https://fcm.googleapis.com/fcm/send"
    data = json.dumps({
        "registration_ids": tokens,
        "notification": {
            "title": title,
            "body": text,
            "payload": {
                'id': link_id,
                "status": status
            }
        }
    })
    headers = {
        'Authorization': f'key={config("SECRET_KEY")}',
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=data)

    if response.status_code == 200:
        pass
    else:
        print(f"Failed to send push notification. Status code: {response.status_code}")


def username_is_valid(username):
    if re.match("^[a-zA-Z0-9]+$", username) and len(username) > 5:
        return True
    return False


def pwd_is_valid(username):
    if re.match("^[a-zA-Z0-9]+$", username) and len(username) > 6:
        return True
    return False


def create_notification_by_order(order: MyOrder):
    auto_not = AutoNotification.objects.filter(status='order', obj_status=order.status).first()
    if auto_not:
        Notification.objects.create(
            user=order.author.user,
            status='order',
            title=auto_not.title,
            description=auto_not.text,
            link_id=order.id,
            is_pushed=True
        )


def create_notification_by_wallet(balance: BalancePlus):
    if not balance.is_moderation:
        auto_not = AutoNotification.objects.filter(status='balance', obj_status='created').first()
    elif balance.is_success:
        auto_not = AutoNotification.objects.filter(status='balance', obj_status='success').first()
    else:
        auto_not = AutoNotification.objects.filter(status='balance', obj_status='rejected').first()

    if auto_not:
        Notification.objects.create(
            user=balance.dealer.user,
            status='balance',
            title=auto_not.title,
            description=auto_not.text,
            link_id=balance.id,
            is_pushed=True
        )


def get_balance_history(user_id, start_date, end_date):
    data = []
    orders = MyOrder.objects.filter(
        author__user_id=user_id, is_active=True, status__in=['success', 'sent', 'wait', 'paid']
    ).values_list('id', 'price', 'created_at')
    balances = MoneyDoc.objects.filter(user_id=user_id, is_active=True).values_list('id', 'amount', 'created_at')
    for order in orders:
        data.append(
            {
                "action_id": order[0],
                "date": order[-1],
                "amount": order[1],
                "type": "order"
            }
        )
    for balance in balances:
        data.append(
            {
                "action_id": balance[0],
                "date": balance[-1],
                "amount": balance[1],
                "type": "wallet"
            }
        )
    result = []
    if data:
        df = pandas.DataFrame(data)
        df = df.sort_values(by="date")
        df['before'] = 0
        df['after'] = 0
        df['date'] = df['date'].astype(str)
        df['amount'] = df['amount'].astype(int)

        balance = 0

        for index, row in df.iterrows():
            df.at[index, 'before'] = balance
            before_balance = balance
            if row['type'] == 'wallet':
                balance += row['amount']
            elif row['type'] == 'order':
                balance -= row['amount']

            df.at[index, 'after'] = balance

            comparison_date_str = row['date']
            history_date = datetime.datetime.fromisoformat(comparison_date_str)
            if start_date <= history_date < end_date:
                result.append(
                    {
                        'action_id': row['action_id'],
                        'created_at': row['date'],
                        'amount': row['amount'],
                        'status': row['type'],
                        'before': before_balance,
                        'after': balance,
                    }
                )

    if result:
        result.reverse()
    return result
