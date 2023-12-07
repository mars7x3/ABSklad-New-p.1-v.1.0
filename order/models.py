from django.db import models

from account.models import DealerProfile
from general_service.models import City, Stock, CashBox
from product.models import AsiaProduct, Category


class MyOrder(models.Model):
    STATUS = (
        ('Новый', 'Новый'),
        ('Оплачено', 'Оплачено'),
        ('Отправлено', 'Отправлено'),
        ('Ожидание', 'Ожидание'),
        ('Отказано', 'Отказано'),
        ('Успешно', 'Успешно')
    )
    TYPE_STATUS = (
        ('Наличка', 'Наличка'),
        ('Карта', 'Карта'),
        ('Баллы', 'Баллы'),
        ('Каспи', 'Каспи')
    )
    author = models.ForeignKey(DealerProfile, on_delete=models.SET_NULL, blank=True, null=True, related_name='orders')
    name = models.CharField(max_length=100, blank=True, null=True)
    gmail = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=100, blank=True, null=True)
    address = models.CharField(max_length=300, blank=True, null=True)
    stock = models.ForeignKey(Stock, on_delete=models.SET_NULL, null=True, related_name='orders')
    price = models.DecimalField(max_digits=100, decimal_places=2, default=0)
    cost_price = models.DecimalField(max_digits=100, decimal_places=2, default=0)
    status = models.CharField(choices=STATUS, max_length=15, default='Новый')
    type_status = models.CharField(choices=TYPE_STATUS, max_length=15, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    uid = models.CharField(max_length=50, default='00000000-0000-0000-0000-000000000000')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('-created_at',)


class OrderMoney(models.Model):
    order = models.ForeignKey(MyOrder, on_delete=models.CASCADE, related_name='order_receipts')
    amount = models.DecimalField(max_digits=100, decimal_places=2, default=0)
    cash_box = models.ForeignKey(CashBox, on_delete=models.SET_NULL, blank=True, null=True, related_name='orders')
    uid = models.CharField(max_length=50, default='00000000-0000-0000-0000-000000000000')
    created_at = models.DateTimeField(auto_now_add=True)


class OrderReceipt(models.Model):
    order = models.ForeignKey(MyOrder, on_delete=models.CASCADE, related_name='order_receipts')
    file = models.FileField(upload_to='order-check')
    created_at = models.DateTimeField(auto_now_add=True)


class OrderProduct(models.Model):
    order = models.ForeignKey(MyOrder, on_delete=models.CASCADE, related_name='order_products')
    ab_product = models.ForeignKey(AsiaProduct, on_delete=models.SET_NULL, related_name='order_products',
                                   blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, blank=True, null=True,
                                 related_name='order_products')
    title = models.CharField(max_length=500)
    count = models.DecimalField(max_digits=100, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=100, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=100, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=100, decimal_places=2, default=0)  # сумма скидки
    image = models.FileField(upload_to='order-product', blank=True, null=True)


class ReturnOrder(models.Model):
    STATUS = (
        ('Новый', 'Новый'),
        ('Успешно', 'Успешно'),
        ('Отказано', 'Отказано'),
    )
    order = models.ForeignKey(MyOrder, on_delete=models.CASCADE, related_name='returns')
    status = models.CharField(max_length=10, choices=STATUS, default='Новый')
    created_at = models.DateTimeField(auto_now_add=True)
    moder_comment = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ('-id',)


class ReturnOrderProduct(models.Model):
    returns_order = models.ForeignKey(ReturnOrder, on_delete=models.CASCADE, related_name='return_products')
    product = models.ForeignKey(AsiaProduct, on_delete=models.CASCADE, related_name='return_products')
    count = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=100, decimal_places=2, default=0)


class Cart(models.Model):
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE, related_name='carts')
    stock = models.OneToOneField(Stock, on_delete=models.CASCADE, related_name='cart')


class CartProduct(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_products')
    product = models.ForeignKey(AsiaProduct, on_delete=models.CASCADE, related_name='cart_products')
    count = models.IntegerField(default=0)

