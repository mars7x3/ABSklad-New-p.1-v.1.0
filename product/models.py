from django.db import models

from account.models import DealerStatus, MyUser
from general_service.models import City, Stock


class Category(models.Model):
    title = models.CharField(max_length=100)
    slug = models.CharField(max_length=100, unique=True)
    image = models.FileField(upload_to='category', blank=True, null=True)
    uid = models.CharField(max_length=50, default='00000000-0000-0000-0000-000000000000')
    is_active = models.BooleanField(default=False)
    is_show = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=['slug'])
        ]


class Collection(models.Model):
    title = models.CharField(max_length=200)
    slug = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=['slug'])
        ]


class AsiaProduct(models.Model):
    is_active = models.BooleanField(default=False)
    is_show = models.BooleanField(default=False)
    is_hit = models.BooleanField(default=False)
    uid = models.CharField(max_length=40, default='00000000-0000-0000-0000-000000000000')
    title = models.CharField(max_length=500)
    vendor_code = models.CharField(max_length=50, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    collection = models.ForeignKey(Collection, on_delete=models.SET_NULL, null=True, related_name='products')
    made_in = models.CharField(max_length=50)
    guarantee = models.IntegerField(default=0)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    video_link = models.TextField(blank=True, null=True)
    weight = models.IntegerField(default=0)
    package_count = models.IntegerField(default=0)
    avg_rating = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    reviews_count = models.IntegerField(default=0)
    diagram = models.FileField(upload_to='product_diagrams', blank=True, null=True)

    def __str__(self):
        return f"{self.vendor_code}. {self.title}"

    class Meta:
        ordering = ('-updated_at',)


class ProductCostPrice(models.Model):
    product = models.ForeignKey(AsiaProduct, on_delete=models.CASCADE, related_name='cost_prices')
    price = models.DecimalField(max_digits=100, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ProductPrice(models.Model):
    STATUS = (
        ('Per', 'Per'),
        ('Sum', 'Sum'),
    )
    product = models.ForeignKey(AsiaProduct, on_delete=models.CASCADE, related_name='prices')
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='prices')
    d_status = models.ForeignKey(DealerStatus, on_delete=models.CASCADE, related_name='prices')
    price = models.DecimalField(max_digits=100, decimal_places=2, default=0)
    old_price = models.DecimalField(max_digits=100, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=100, decimal_places=2, default=0)
    discount_status = models.CharField(max_length=5, choices=STATUS, default='Per')

    def __str__(self):
        return f'{self.product} - {self.city} - {self.price}'


class ProductCount(models.Model):
    product = models.ForeignKey(AsiaProduct, on_delete=models.CASCADE, related_name='counts')
    stock = models.ForeignKey(Stock, on_delete=models.SET_NULL, null=True, related_name='counts')
    count_crm = models.IntegerField(default=0)
    count_1c = models.IntegerField(default=0)
    count_order = models.IntegerField(default=0)
    arrival_time = models.DateTimeField(blank=True, null=True)


class ProductSize(models.Model):
    product = models.ForeignKey(AsiaProduct, on_delete=models.CASCADE, related_name='sizes')
    title = models.CharField(max_length=200, blank=True, null=True)
    length = models.IntegerField(default=0)
    width = models.IntegerField(default=0)
    height = models.IntegerField(default=0)


class ProductImage(models.Model):
    product = models.ForeignKey(AsiaProduct, on_delete=models.CASCADE, related_name='images')
    image = models.FileField(upload_to='product-images')
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ('position',)


class Review(models.Model):
    product = models.ForeignKey(AsiaProduct, on_delete=models.CASCADE, related_name='reviews')
    author = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='reviews')
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    is_active = models.BooleanField(default=True)
    is_moderation = models.BooleanField(default=False)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.rating} - {self.text}'

    class Meta:
        ordering = ('-id',)


class ReviewImage(models.Model):
    product = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product-images')


class FilterMaxMin(models.Model):
    max_price = models.PositiveIntegerField(default=0)
    min_price = models.PositiveIntegerField(default=0)


