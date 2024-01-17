from typing import Callable

from django.db import models
from django.db.models.functions import ExtractMonth, ExtractYear, TruncDate, JSONObject
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


class PurchasesQuerySet(models.QuerySet):
    def group_by_date(self, by_field: str, date_trunc: Callable = TruncDate):
        return self.values(by_field, stat_date=date_trunc("date"))

    def annotate_month_and_year(self):
        return self.annotate(month=ExtractMonth('date'), year=ExtractYear('date'))

    def annotate_sales(self):
        return (
            self.annotate(
                sales_products_count=models.Count(
                    "product_stat__product_id",
                    distinct=True
                ),
                sales_amount=models.Sum(
                    "spent_amount",
                    default=models.Value(0.0)
                ),
                sales_count=models.Count("id"),
                sales_users_count=models.Count("user_stat__user_id", distinct=True)
            )
            .annotate(
                sales_avg_check=models.Case(
                    models.When(sales_amount__gt=0, sales_count__gt=0,
                                then=models.F("sales_amount") / models.F("sales_count")),
                    default=models.Value(0.0),
                    output_field=models.DecimalField()
                ),
            )
        )

    def annotate_funds(self, date_trunc: Callable = None, **sub_filters):
        tx_base_query = UserTransactionsStat.objects.filter(**sub_filters)
        if date_trunc:
            tx_subquery = (
                tx_base_query
                .values("bank_income", "cash_income")
                .annotate(stat_date=date_trunc("date"))
                .filter(stat_date=models.OuterRef("stat_date"))
            )
            incoming_users_query = (
                tx_base_query
                .values(stat_date=date_trunc("date"))
                .filter(stat_date=models.OuterRef("stat_date"))
            )
        else:
            tx_subquery = tx_base_query
            incoming_users_query = tx_base_query

        return (
            self.annotate(
                bank_amount=models.Subquery(
                    tx_subquery
                    .annotate(bank_amount=models.Sum("bank_income"))
                    .values("bank_amount")[:1]
                ),
                cash_amount=models.Subquery(
                    tx_subquery
                    .annotate(cash_amount=models.Sum("cash_income"))
                    .values("cash_amount")[:1]
                ),
                users_count=models.Subquery(
                    incoming_users_query
                    .annotate(users_count=models.Count("user_stat__user_id", distinct=True))
                    .values("users_count")[:1]
                )
            )
            .annotate(
                incoming_bank_amount=models.Case(
                    models.When(bank_amount__isnull=True, then=models.Value(0.0)),
                    default=models.F("bank_amount"),
                    output_field=models.DecimalField()
                ),
                incoming_cash_amount=models.Case(
                    models.When(cash_amount__isnull=True, then=models.Value(0.0)),
                    default=models.F("cash_amount"),
                    output_field=models.DecimalField()
                ),
                incoming_users_count=models.Case(
                    models.When(users_count__isnull=True, then=models.Value(0)),
                    default=models.F("users_count"),
                    output_field=models.IntegerField()
                )
            )
        )


class PurchaseStat(BaseStatistics):
    objects = PurchasesQuerySet.as_manager()

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
