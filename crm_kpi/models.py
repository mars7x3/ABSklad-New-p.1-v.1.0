from django.db import models

from account.models import MyUser
from product.models import AsiaProduct


class DealerKPI(models.Model):
    user = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='kpis')
    is_confirmed = models.BooleanField(default=False)
    pds = models.DecimalField(decimal_places=2, max_digits=100, default=0)
    fact_pds = models.DecimalField(decimal_places=2, max_digits=100, default=0)
    month = models.DateField()
    per_cent_pds = models.PositiveIntegerField(default=0)
    per_cent_tmz = models.PositiveIntegerField(default=0)


class DealerKPIProduct(models.Model):
    kpi = models.ForeignKey(DealerKPI, on_delete=models.CASCADE, related_name='kpi_products')
    product = models.ForeignKey(AsiaProduct, on_delete=models.CASCADE, related_name='kpi_products')
    count = models.PositiveIntegerField()
    fact_count = models.PositiveIntegerField(default=0)
    fact_sum = models.DecimalField(decimal_places=2, max_digits=100, default=0)
    sum = models.DecimalField(decimal_places=2, max_digits=100, default=0)


class ManagerKPITMZInfo(models.Model):
    per_cent = models.PositiveIntegerField(default=0)
    bonus = models.DecimalField(max_digits=100, decimal_places=2, default=0)


class ManagerKPIPDSInfo(models.Model):
    per_cent = models.PositiveIntegerField(default=0)
    coefficient = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=100, decimal_places=2, default=0)

