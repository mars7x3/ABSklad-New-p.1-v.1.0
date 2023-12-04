from django.db import models

from account.models import DealerProfile
from product.models import AsiaProduct


class Story(models.Model):
    is_active = models.BooleanField(default=False)
    title = models.CharField(max_length=300)
    slogan = models.CharField(max_length=300)
    text = models.TextField()
    image = models.FileField(upload_to='stories_files', blank=True, null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    products = models.ManyToManyField(AsiaProduct, related_name='stories')


class Target(models.Model):
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE, related_name='targets')
    total_amount = models.DecimalField(max_digits=100, decimal_places=2, default=0)
    completed = models.DecimalField(max_digits=100, decimal_places=2, default=0)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)


class TargetPresent(models.Model):
    STATUS = (
        ('product', 'Товар'),
        ('money', 'Деньги'),
        ('text', 'Прочее'),
    )
    target = models.ForeignKey(Target, on_delete=models.CASCADE, related_name='presents')
    status = models.CharField(max_length=10, choices=STATUS, default='money')
    product = models.ForeignKey(AsiaProduct, on_delete=models.SET_NULL, blank=True, null=True,
                                related_name='present_products')
    text = models.TextField(blank=True, null=True)
    money = models.DecimalField(max_digits=100, decimal_places=2, default=0)



