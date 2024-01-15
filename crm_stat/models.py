from django.db import models
from django.utils.translation import gettext_lazy as _

from account.models import MyUser
from general_service.models import City, Stock
from product.models import Category, Collection, AsiaProduct


class CityStat(models.Model):
    objects = models.Manager()

    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class UserStat(models.Model):
    objects = models.Manager()

    city_stat = models.ForeignKey(CityStat, on_delete=models.CASCADE, related_name='users')
    user = models.ForeignKey(MyUser, on_delete=models.SET_NULL, null=True)
    email = models.EmailField(max_length=100)
    name = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{getattr(self, 'id')}.{self.name}"


class StockStat(models.Model):
    objects = models.Manager()

    stock = models.ForeignKey(Stock, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=100)
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=False)
    city_stat = models.ForeignKey(CityStat, on_delete=models.CASCADE, related_name='stocks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ProductStat(models.Model):
    objects = models.Manager()

    product = models.ForeignKey(AsiaProduct, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=500)
    vendor_code = models.CharField(max_length=50, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    collection = models.ForeignKey(Collection, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class BaseStatistics(models.Model):
    """
    inherited from this class will contain a record for a specific day
    """
    objects = models.Manager()

    date = models.DateField()

    class Meta:
        abstract = True


class UserTransactionsStat(BaseStatistics):
    user_stat = models.ForeignKey(UserStat, on_delete=models.CASCADE, related_name='transactions')
    stock_stat = models.ForeignKey(StockStat, on_delete=models.CASCADE, related_name="transactions")
    bank_income = models.DecimalField(max_digits=10, decimal_places=2)
    cash_income = models.DecimalField(max_digits=10, decimal_places=2)


class PurchaseStat(BaseStatistics):  # required
    user_stat = models.ForeignKey(UserStat, on_delete=models.CASCADE, related_name='purchases')
    product_stat = models.ForeignKey(ProductStat, on_delete=models.CASCADE, related_name='purchases')
    stock_stat = models.ForeignKey(StockStat, on_delete=models.CASCADE, related_name='purchases')
    spent_amount = models.DecimalField(max_digits=20, decimal_places=2)
    count = models.PositiveIntegerField()
    purchases_count = models.PositiveIntegerField(default=0)
    avg_check = models.DecimalField(max_digits=20, decimal_places=2, default=0)


class StockGroupStat(BaseStatistics):
    class StatType(models.TextChoices):
        month = "month", _("Month")
        day = "day", _("Day")

    stat_type = models.CharField(max_length=10, choices=StatType.choices)
    stock_stat = models.ForeignKey(StockStat, on_delete=models.CASCADE, related_name="group_stats")

    incoming_bank_amount = models.DecimalField(decimal_places=2, max_digits=20, default=0)
    incoming_cash_amount = models.DecimalField(decimal_places=2, max_digits=20, default=0)
    incoming_users_count = models.IntegerField(default=0)

    sales_products_count = models.IntegerField(default=0)
    sales_amount = models.DecimalField(decimal_places=2, max_digits=20, default=0)
    sales_count = models.IntegerField(default=0)
    sales_users_count = models.IntegerField(default=0)
    sales_avg_check = models.DecimalField(decimal_places=2, max_digits=20, default=0)

    dealers_incoming_funds = models.DecimalField(decimal_places=2, max_digits=20, default=0)
    dealers_products_count = models.IntegerField(default=0)
    dealers_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    dealers_avg_check = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    products_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    products_user_count = models.IntegerField(default=0)
    products_avg_check = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    class Meta:
        unique_together = ["stat_type", "stock_stat", "date"]
