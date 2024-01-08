from django.db import models

from account.models import MyUser
from general_service.models import Stock


class PDS(models.Model):
    user = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='pds')
    bank_income = models.PositiveIntegerField(default=0)
    box_office_income = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class Stat(models.Model):
    user = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='counter_agents')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='stats')
    product = models.ForeignKey('product.AsiaProduct', on_delete=models.CASCADE, related_name='stats')
    count = models.PositiveIntegerField(default=0)
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    cost_price = models.DecimalField(max_digits=9, decimal_places=2, default=0)

