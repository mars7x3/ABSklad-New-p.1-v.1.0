import random
import requests


def random_code():
    code = [random.randint(1, 10) for _ in range(4)]
    code = [str(i) for i in code]
    code = ''.join(code)
    return code


def send_code_to_email(email):
    pass


def send_code_to_phone(phone, text):
    api_key = 'kz4dff49ea3b3dd2237043ca1aae22a095664e726e025a8c34e822da61458c0d2620b3'
    api_url = 'http://api.mobizon.kz/service/message/'
    params = {
        'recipient': phone,
        'text': text,
        'apiKey': api_key
    }
    # Отправка SMS
    response = requests.get(api_url + 'sendsmsmessage', params=params)
    print(response.json())


