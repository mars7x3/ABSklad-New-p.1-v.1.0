import re
from pprint import pprint

import requests
import json
from django.utils.crypto import get_random_string
from decouple import config
from account.models import MyUser, BalanceHistory


def random_code():
    code = get_random_string(length=4, allowed_chars='0123456789')
    print(code)
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
    print(api_url)
    response = requests.get(api_url, params=params)
    print(response.json())


def generate_pwd() -> str:
    password = get_random_string(length=8,
                                 allowed_chars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    return password


def send_push_notification(users, title, text, link_id, status):
    url = "https://fcm.googleapis.com/fcm/send"
    tokens = [user.firebase_token for user in users]
    payload = json.dumps({
      "registration_ids": tokens,
      "notification": {
          "title": title,
          "body": text,
          "payload": {
              "id": link_id,
              "status": status
          }
      }
    })
    headers = {
        'Authorization': f'key={config("SECRET_KEY")}',
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)


def sync_balance_history(data, type_status):
    if type_status == 'order':
        balance = data.author.wallet.amount_crm
        dealer = data.author
        amount = data.price
    else:
        balance = data.user.dealer_profile.wallet.amount_crm
        dealer = data.user.dealer_profile
        amount = data.amount

    validated_data = {
        'dealer': dealer,
        'amount': amount,
        'status': type_status,
        'action_id': data.id,
        'is_active': data.is_active,
        'created_at': data.created_at,
        'balance': balance
    }

    history = BalanceHistory.objects.filter(status=type_status, action_id=data.id)
    if history:
        pprint(validated_data)
        for key, value in validated_data.items():
            setattr(history, key, value)
        history.save()
        print(history.is_active)
    else:
        BalanceHistory.objects.create(**validated_data)


def username_is_valid(username):
    if re.match("^[a-zA-Z0-9]+$", username) and len(username) > 5:
        return True
    return False


def pwd_is_valid(username):
    if re.match("^[a-zA-Z0-9]+$", username) and len(username) > 6:
        return True
    return False

