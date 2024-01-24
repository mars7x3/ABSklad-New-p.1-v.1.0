from django.db import models

from account.models import DealerProfile, DealerStatus, MyUser
from general_service.compress import WEBPField, banner_image_folder
from general_service.models import City
from product.models import AsiaProduct, Category


class Story(models.Model):
    is_active = models.BooleanField(default=False)
    title = models.CharField(max_length=300)
    slogan = models.CharField(max_length=300)
    text = models.TextField()
    file = models.FileField(upload_to='stories_files', blank=True, null=True)
    clicks = models.PositiveIntegerField(default=0)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    products = models.ManyToManyField(AsiaProduct, related_name='stories')
    dealer_profiles = models.ManyToManyField(DealerProfile, related_name='stories')

    class Meta:
        ordering = ('-id',)


class Motivation(models.Model):
    title = models.CharField(max_length=300)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    dealers = models.ManyToManyField(DealerProfile, blank=True, related_name='motivations')


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
    condition = models.ForeignKey(MotivationCondition, on_delete=models.CASCADE, related_name='condition_cats')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='condition_cats')
    count = models.IntegerField(default=0)


class ConditionProduct(models.Model):
    condition = models.ForeignKey(MotivationCondition, on_delete=models.CASCADE, related_name='condition_prods')
    product = models.ForeignKey(AsiaProduct, on_delete=models.CASCADE, related_name='condition_prods')
    count = models.IntegerField(default=0)


class MotivationPresent(models.Model):
    STATUS = (
        ('money', 'Деньги'),
        ('text', 'Прочее')
    )
    condition = models.ForeignKey(MotivationCondition, on_delete=models.CASCADE, null=True, related_name='presents')
    status = models.CharField(max_length=10, choices=STATUS, default='money')
    money = models.DecimalField(max_digits=100, decimal_places=2, default=0)
    expense = models.DecimalField(max_digits=100, decimal_places=2, default=0)
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
    dealer_profiles = models.ManyToManyField(DealerProfile, related_name='discount_d_profiles')

    class Meta:
        ordering = ('-created_at',)


class Banner(models.Model):
    title = models.CharField(max_length=255)
    is_active = models.BooleanField(default=False)
    motivation = models.ForeignKey(Motivation, on_delete=models.CASCADE, related_name='banners', blank=True, null=True)
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name='banners', blank=True, null=True)
    image = WEBPField(upload_to=banner_image_folder, null=True, blank=True)  # TODO: delete null=True after demo version
    web_image = models.ImageField(upload_to='banner-images', blank=True, null=True)  # TODO: delete after demo version
    video_url = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    clicks = models.PositiveIntegerField(default=0)
    show_date = models.BooleanField(default=False)
    products = models.ManyToManyField(AsiaProduct, related_name='banners', blank=True)
    dealer_profiles = models.ManyToManyField(DealerProfile, related_name='banners', blank=True)

    class Meta:
        ordering = ('-created_at',)
