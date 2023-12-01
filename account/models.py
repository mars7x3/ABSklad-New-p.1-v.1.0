from django.contrib.auth.models import AbstractUser
from django.db import models

from general_service.models import City


class DealerStatus(models.Model):
    title = models.CharField(max_length=50, blank=True, null=True)
    discount = models.IntegerField(default=0)

    def __str__(self):
        return self.title


class MyUser(AbstractUser):
    STATUS = (
        ('director', 'Директор'),
        ('main_manager', 'РОП'),
        ('manager', 'Менеджер'),
        ('marketer', 'Маркетолог'),
        ('accountant', 'Бухгалтер'),
        ('dealer', 'Дилер'),
        ('warehouse', 'Зав. Склад'),
        ('dealer_1c', 'dealer_1c'),
    )

    email = models.EmailField(unique=True)
    status = models.CharField(choices=STATUS, max_length=20, blank=True, null=True)
    uid = models.CharField(max_length=40, default='00000000-0000-0000-0000-000000000000')
    pwd = models.CharField(max_length=40, blank=True, null=True)

    def __str__(self):
        return f'{self.id}.{self.email or self.username}'

    class Meta:
        ordering = ('-date_joined',)

    @property
    def is_manager(self) -> bool:
        return self.status == 'manager'

    @property
    def is_dealer(self) -> bool:
        return self.status == 'dealer'


class StaffProfile(models.Model):
    user = models.OneToOneField(MyUser, on_delete=models.CASCADE, related_name='staff_profile')
    city = models.ForeignKey(City, on_delete=models.SET_NULL, blank=True, null=True, related_name='staff_profiles')
    name = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)


class DealerProfile(models.Model):
    user = models.OneToOneField(MyUser, on_delete=models.CASCADE, related_name='dealer_profile')
    city = models.ForeignKey(City, on_delete=models.SET_NULL, blank=True, null=True, related_name='dealer_profiles')
    name = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=300, blank=True, null=True)
    image = models.ImageField(upload_to='dealer_avatar', blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    dealer_status = models.ForeignKey(DealerStatus, on_delete=models.SET_NULL, blank=True, null=True,
                                      related_name='dealer_profiles')
    liability = models.PositiveIntegerField(default=0)
    price_city = models.ForeignKey(City, on_delete=models.SET_NULL, blank=True, null=True)
    push_notification = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class DealerStore(models.Model):
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE, related_name='dealer_stores')
    city = models.ForeignKey(City, on_delete=models.SET_NULL, blank=True, null=True)
    title = models.CharField(max_length=200, blank=True, null=True)
    address = models.TextField(blank=True, null=True)


class Wallet(models.Model):
    user = models.OneToOneField(DealerProfile, on_delete=models.CASCADE, null=True, related_name='wallet')
    amount_crm = models.DecimalField(default=0, max_digits=100, decimal_places=2)
    amount_1c = models.DecimalField(default=0, max_digits=100, decimal_places=2)

    def __str__(self):
        return f'{self.id}'


class BalancePlus(models.Model):
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE, null=True, related_name='balances')
    amount = models.DecimalField(default=0, max_digits=100, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    is_moderation = models.BooleanField(default=False)
    is_success = models.BooleanField(default=False)
    comment = models.TextField(blank=True, null=True)


class BalancePlusFile(models.Model):
    balance = models.ForeignKey(BalancePlus, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='balance_plus_images')


class Notification(models.Model):
    STATUS = (
        ('order', 'Заказ'),
        ('news', 'Новости'),
        ('action', 'Акция'),
        ('notif', 'Оповещение'),
        ('chat', 'Чат'),
        ('balance', 'Пополнение баланса'),

    )
    user = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='notifications')
    status = models.CharField(choices=STATUS, max_length=10, blank=True, null=True)
    image = models.FileField(upload_to='notification', blank=True, null=True)
    is_read = models.BooleanField(default=False)
    title = models.CharField(max_length=300, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    link_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_push = models.BooleanField(default=False)

    class Meta:
        ordering = ('-id',)


class VerifyCode(models.Model):
    user = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='verify_codes')
    code = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)
