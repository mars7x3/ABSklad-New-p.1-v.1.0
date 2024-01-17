import random
import requests
from django.utils.crypto import get_random_string


def random_code():
    code = get_random_string(length=4, allowed_chars='0123456789')
    print(code)
    return code


def send_code_to_email(email):
    pass


def send_code_to_phone(phone, text):
    api_key = 'kz4dff49ea3b3dd2237043ca1aae22a095664e726e025a8c34e822da61458c0d2620b3'
    api_url = 'https://api.mobizon.kz/service/message/sendsmsmessage'
    text = 'ASIA BRAND: ' + text
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
