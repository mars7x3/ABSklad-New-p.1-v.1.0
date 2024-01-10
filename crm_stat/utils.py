from django.core.exceptions import ObjectDoesNotExist

from general_service.models import Stock
from product.models import AsiaProduct
from .models import PDS, Stat
from account.models import MyUser


def fill_pds_stat(user_id: int, bank_income=0, box_office_income=0):
    try:
        user = MyUser.objects.get(id=user_id)
    except ObjectDoesNotExist:
        return {'detail': f'user with {user_id} does not exist'}
    try:
        if bank_income and box_office_income:
            return {'detail': 'Only one of options (bank_income or box_office_income) needed'}
        if bank_income:
            PDS.objects.create(user=user, bank_income=bank_income)
            return True
        elif box_office_income:
            PDS.objects.create(user=user, box_office_income=box_office_income)
            return True
    except Exception as e:
        print(e)
        return False


def fill_stat(user: MyUser, stock: Stock, product: AsiaProduct, count=0, amount=0, cost_price=0):
    try:
        Stat.objects.create(user=user, stock=stock, product=product, count=count, amount=amount, cost_price=cost_price)
        return True
    except Exception as e:
        print(e)
        return False


