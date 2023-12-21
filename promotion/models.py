from django.db import models

from account.models import DealerProfile, DealerStatus, MyUser
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
    cities = models.ManyToManyField(City, related_name='stories')
    dealer_groups = models.ManyToManyField(DealerStatus, related_name='stories')


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
    STATUS = (
        ('Per', 'Per'),
        ('Sum', 'Sum'),
    )
    is_active = models.BooleanField(default=False)
    title = models.CharField(max_length=300)
    status = models.CharField(max_length=5, choices=STATUS, default='Per')
    amount = models.DecimalField(max_digits=100, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    products = models.ManyToManyField(AsiaProduct, related_name='discount_products')
    cities = models.ManyToManyField(City, related_name='discount_cities')
    dealer_statuses = models.ManyToManyField(DealerStatus, related_name='discount_d_statuses')


class Banner(models.Model):
    STATUS = (
        ('web', 'web'),
        ('app', 'app'),
    )

    title = models.CharField(max_length=255)
    is_active = models.BooleanField(default=False)
    video_url = models.CharField(max_length=1000)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(choices=STATUS, default='web', max_length=3)
    created_at = models.DateTimeField(auto_now_add=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    clicks = models.PositiveIntegerField(default=0)
    cities = models.ManyToManyField(City, related_name='banners')
    products = models.ManyToManyField(AsiaProduct, related_name='banners')
    groups = models.ManyToManyField(DealerStatus, related_name='banner_groups')
