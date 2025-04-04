from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

from general_service.compress import WEBPField, user_image_folder, notification_image_folder
from general_service.models import City, Stock, PriceType, Village


class DealerStatus(models.Model):
    title = models.CharField(max_length=50, blank=True, null=True)
    discount = models.IntegerField(default=0)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class MyUserManager(UserManager):
    def _create_user(self, username, email, password, **extra_fields):
        if not extra_fields.get('is_super_user'):
            extra_fields.setdefault('pwd', password)
        return super()._create_user(username, email, password, **extra_fields)


class MyUser(AbstractUser):
    objects = MyUserManager()

    STATUS = (
        ('main_director', 'Директор'),  # has no profile
        ('director', 'Ком Директор'),  # has no profile
        ('rop', 'РОП'),
        ('manager', 'Менеджер'),
        ('marketer', 'Маркетолог'),  # has no profile
        ('accountant', 'Бухгалтер'),  # has no profile
        ('dealer', 'Дилер'),
        ('warehouse', 'Зав. Склад'),
        ('dealer_1c', 'dealer_1c'),
        ('hr', 'HR менеджер'),
    )

    email = models.EmailField(unique=True)
    status = models.CharField(choices=STATUS, max_length=20, blank=True, null=True)
    uid = models.CharField(max_length=40, default='00000000-0000-0000-0000-000000000000')
    pwd = models.CharField(max_length=40, blank=True, null=True)

    name = models.CharField(max_length=50, blank=True, null=True)
    image = WEBPField(upload_to=user_image_folder, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    firebase_token = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.id}.{self.email or self.username}'

    class Meta:
        ordering = ('-date_joined',)

    def set_password(self, raw_password):
        self.pwd = raw_password
        super().set_password(raw_password)

    @property
    def is_manager(self) -> bool:
        return self.status == 'manager'

    @property
    def is_dealer(self) -> bool:
        return self.status == 'dealer'

    @property
    def is_rop(self) -> bool:
        return self.status == 'rop'


class StaffMagazine(models.Model):
    STATUS = (
        ('new', 'Новый'),
        ('hired', 'Принят на работу'),
        ('fired', 'Уволен'),
        ('vacation', 'Отпуск'),
        ('restored', 'Востановлен'),
    )
    user = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='magazines')
    status = models.CharField(choices=STATUS, max_length=20, default='new')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now=True)


class RopProfile(models.Model):
    user = models.OneToOneField(MyUser, on_delete=models.CASCADE, related_name='rop_profile')
    cities = models.ManyToManyField(City, related_name='rop_profiles')
    managers = models.ManyToManyField('ManagerProfile', related_name='managers')


class ManagerProfile(models.Model):
    user = models.OneToOneField(MyUser, on_delete=models.CASCADE, related_name='manager_profile')
    is_main = models.BooleanField(default=False)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, related_name='manager_profiles')


class WarehouseProfile(models.Model):
    user = models.OneToOneField(MyUser, on_delete=models.CASCADE, related_name='warehouse_profile')
    stock = models.ForeignKey(Stock, on_delete=models.SET_NULL, null=True, related_name='warehouse_profiles')
    is_main = models.BooleanField(default=False)


class DealerProfile(models.Model):
    STATUS = (
        ('online', 'online'),
        ('offline', 'offline'),
    )
    user = models.OneToOneField(MyUser, on_delete=models.CASCADE, related_name='dealer_profile')
    village = models.ForeignKey(Village, on_delete=models.SET_NULL, blank=True, null=True,
                                related_name='dealer_profiles')
    address = models.CharField(max_length=300, blank=True, null=True)
    dealer_status = models.ForeignKey(DealerStatus, on_delete=models.SET_NULL, blank=True, null=True,
                                      related_name='dealer_profiles')
    liability = models.PositiveIntegerField(default=0)
    price_city = models.ForeignKey(City, on_delete=models.SET_NULL, blank=True, null=True)
    push_notification = models.BooleanField(default=True)
    birthday = models.DateField(blank=True, null=True)
    price_type = models.ForeignKey(PriceType, on_delete=models.SET_NULL, blank=True, null=True,
                                   related_name='dealer_profiles')
    managers = models.ManyToManyField(MyUser, related_name='dealer_profiles', blank=True)
    client_type = models.CharField(max_length=20, choices=STATUS, default='offline')

    def __str__(self):
        return f'{self.id} - {self.user.name}'

    class Meta:
        ordering = ('-id',)


class DealerStore(models.Model):
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE, related_name='dealer_stores')
    city = models.CharField(max_length=200, blank=True, null=True)
    title = models.CharField(max_length=200, blank=True, null=True)
    address = models.TextField(blank=True, null=True)


class Wallet(models.Model):
    dealer = models.OneToOneField(DealerProfile, on_delete=models.CASCADE, blank=True, null=True, related_name='wallet')
    amount_crm = models.DecimalField(default=0, max_digits=100, decimal_places=2)
    amount_1c = models.DecimalField(default=0, max_digits=100, decimal_places=2)

    def __str__(self):
        return f'{self.id}'

    class Meta:
        ordering = ('-amount_1c',)


class BalancePlus(models.Model):
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE, null=True, related_name='balances')
    amount = models.DecimalField(default=0, max_digits=100, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    is_moderation = models.BooleanField(default=False)
    is_success = models.BooleanField(default=False)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ('-id',)


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
        ('motivation', 'Мотивация'),
        ('birthday', 'День рождения'),
        ('recommendation', 'Рекомендация'),
        ('kpi', 'KPI'),
    )

    user = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='notifications')
    status = models.CharField(choices=STATUS, max_length=14, blank=True, null=True)
    image = models.FileField(upload_to='notification', blank=True, null=True)
    is_read = models.BooleanField(default=False)
    title = models.CharField(max_length=300, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    link_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_push = models.BooleanField(default=False)
    per_cent = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('-id',)


class VerifyCode(models.Model):
    user = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='verify_codes')
    code = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)


class CRMNotification(models.Model):
    STATUS = (
        ('order', 'Заказ'),
        ('news', 'Новости'),
        ('action', 'Акция'),
        ('notif', 'Оповещение'),
        ('chat', 'Чат'),
        ('balance', 'Пополнение баланса'),
        ('motivation', 'Мотивация'),
    )

    dealer_profiles = models.ManyToManyField(DealerProfile, related_name='crm_notifications', blank=True)
    image = WEBPField(upload_to=notification_image_folder, blank=True, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    dispatch_date = models.DateTimeField()
    status = models.CharField(choices=STATUS, max_length=100, default='notif')
    link_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_pushed = models.BooleanField(default=False)

    @classmethod
    def get_status_choices(cls):
        return cls.STATUS


class FireBaseToken(models.Model):
    user = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='fb_tokens')
    token = models.TextField()
