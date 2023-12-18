from django.db import models

from account.models import DealerProfile, DealerStatus
from general_service.models import City
from product.models import AsiaProduct, Category


class Story(models.Model):
    is_active = models.BooleanField(default=False)
    title = models.CharField(max_length=300)
    slogan = models.CharField(max_length=300)
    text = models.TextField()
    image = models.FileField(upload_to='stories_files', blank=True, null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    products = models.ManyToManyField(AsiaProduct, related_name='stories')


class Motivation(models.Model):
    title = models.CharField(max_length=300)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    dealers = models.ManyToManyField(DealerProfile, related_name='motivations')


class MotivationCondition(models.Model):
    STATUS = (
        ('category', 'category'),
        ('money', 'money'),
        ('product', 'product')
    )
    status = models.CharField(max_length=10, choices=STATUS)
    motivation = models.ForeignKey(Motivation, on_delete=models.CASCADE, related_name='conditions')
    money = models.DecimalField(max_digits=100, decimal_places=2, default=0)
    text = models.TextField(blank=True, null=True)


class ConditionCategory(models.Model):
    condition = models.ForeignKey(Motivation, on_delete=models.CASCADE, related_name='condition_cats')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='condition_cats')
    count = models.IntegerField(default=0)


class ConditionProduct(models.Model):
    condition = models.ForeignKey(Motivation, on_delete=models.CASCADE, related_name='condition_prods')
    product = models.ForeignKey(AsiaProduct, on_delete=models.CASCADE, related_name='condition_prods')
    count = models.IntegerField(default=0)


class MotivationPresent(models.Model):
    STATUS = (
        ('product', 'Товар'),
        ('money', 'Деньги'),
        ('text', 'Прочее')
    )
    motivation = models.ForeignKey(Motivation, on_delete=models.CASCADE, related_name='presents')
    status = models.CharField(max_length=10, choices=STATUS, default='money')
    product = models.ForeignKey(AsiaProduct, on_delete=models.SET_NULL, blank=True, null=True,
                                related_name='present_products')
    money = models.DecimalField(max_digits=100, decimal_places=2, default=0)
    text = models.TextField(blank=True, null=True)


class Discount(models.Model):
    # banner = models.OneToOneField(Banner, on_delete=models.SET_NULL, blank=True, null=True, related_name='discount')
    title = models.CharField(max_length=300)
    is_active = models.BooleanField(default=False)
    discount_amount = models.DecimalField(max_digits=100, decimal_places=2)
    discount_status = models.BooleanField(default=False)
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)


class DiscountProduct(models.Model):
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name='discount_products')
    product = models.ForeignKey(AsiaProduct, on_delete=models.CASCADE, related_name='discount_products')


class DiscountCity(models.Model):
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name='discount_cities')
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='discount_cities')


class DiscountDealerStatus(models.Model):
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name='discount_d_statuses')
    dealer_status = models.ForeignKey(DealerStatus, on_delete=models.CASCADE, related_name='discount_d_statuses')

