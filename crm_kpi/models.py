from django.db import models

from account.models import MyUser
from product.models import AsiaProduct


class DealerKPI(models.Model):
    user = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='kpis')
    is_confirmed = models.BooleanField(default=False)
    created_by_user = models.BooleanField(default=True)
    pds = models.DecimalField(decimal_places=2, max_digits=100, default=0)
    fact_pds = models.DecimalField(decimal_places=2, max_digits=100, default=0)
    month = models.DateField()
    per_cent_pds = models.PositiveIntegerField(default=0)
    per_cent_tmz = models.PositiveIntegerField(default=0)


class DealerKPIProduct(models.Model):
    kpi = models.ForeignKey(DealerKPI, on_delete=models.CASCADE, related_name='kpi_products')
    product = models.ForeignKey(AsiaProduct, on_delete=models.CASCADE, related_name='kpi_products')
    count = models.PositiveIntegerField(default=0)
    fact_count = models.PositiveIntegerField(default=0)
    fact_sum = models.DecimalField(decimal_places=2, max_digits=100, default=0)
    sum = models.DecimalField(decimal_places=2, max_digits=100, default=0)


class ManagerKPI(models.Model):
    manager = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='mngr_kpis')
    akb = models.PositiveIntegerField(default=0)
    month = models.DateField()


class ManagerKPISVD(models.Model):
    manager_kpi = models.ForeignKey(ManagerKPI, on_delete=models.CASCADE, related_name='svds')
    product = models.ForeignKey(AsiaProduct, on_delete=models.CASCADE, related_name='svds')
    count = models.PositiveIntegerField(default=0)


class ManagerKPIInfo(models.Model):
    STATUS = (
        ('svd', 'svd'),
        ('akb', 'akb'),
        ('tmz', 'tmz'),
        ('sch', 'sch'),
        ('pds', 'pds'),
    )
    status = models.CharField(choices=STATUS, max_length=10)
    manager_kpi = models.ForeignKey(ManagerKPI, on_delete=models.CASCADE, related_name='mngr_info')
    per_cent = models.PositiveIntegerField(default=0)
    bonus = models.DecimalField(max_digits=100, decimal_places=2, default=0)

