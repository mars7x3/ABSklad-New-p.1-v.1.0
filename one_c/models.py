from django.db import models

from account.models import MyUser
from general_service.models import CashBox
from order.models import MyOrder


class MoneyDoc(models.Model):
    STATUS = (
        ('Нал', 'Нал'),
        ('Без нал', 'Без нал')
    )
    status = models.CharField(choices=STATUS, max_length=10, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    user = models.ForeignKey(MyUser, on_delete=models.SET_NULL, null=True, related_name='money_docs')
    amount = models.DecimalField(max_digits=100, decimal_places=2, default=0)
    cash_box = models.ForeignKey(CashBox, on_delete=models.SET_NULL, null=True, related_name='money_docs')
    uid = models.CharField(max_length=50, default='00000000-0000-0000-0000-000000000000')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



