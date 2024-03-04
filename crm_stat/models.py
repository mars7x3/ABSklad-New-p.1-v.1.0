from typing import Callable

from django.db import models
from django.utils.translation import gettext_lazy as _


class BaseStatistics(models.Model):
    """
    inherited from this class will contain a record for a specific day
    """
    objects = models.Manager()

    date = models.DateField()

    class Meta:
        abstract = True


class UserTransactionsStat(BaseStatistics):
    user = models.ForeignKey("account.MyUser", on_delete=models.CASCADE, related_name='transactions')
    stock = models.ForeignKey("general_service.Stock", on_delete=models.CASCADE, related_name="transactions")
    bank_income = models.DecimalField(max_digits=20, decimal_places=2)
    cash_income = models.DecimalField(max_digits=20, decimal_places=2)


class PurchasesQuerySet(models.QuerySet):
    def annotate_funds(self, date_trunc: Callable = None, **sub_filters):
        tx_base_query = UserTransactionsStat.objects.filter(**sub_filters)
        if date_trunc:
            tx_subquery = (
                tx_base_query
                .annotate(stat_date=date_trunc("date"))
                .filter(stat_date=models.OuterRef("stat_date"))
                .values("stat_date")
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
                    .annotate(users_count=models.Count("user_id", distinct=True))
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

    user = models.ForeignKey("account.MyUser", on_delete=models.CASCADE, related_name='purchases')
    product = models.ForeignKey("product.AsiaProduct", on_delete=models.CASCADE, related_name='purchases')
    stock = models.ForeignKey("general_service.Stock", on_delete=models.CASCADE, related_name='purchases')
    spent_amount = models.DecimalField(max_digits=20, decimal_places=2)
    count = models.PositiveIntegerField()
    purchases_count = models.PositiveIntegerField(default=0)
    avg_check = models.DecimalField(max_digits=20, decimal_places=2, default=0)


class StockGroupStat(BaseStatistics):
    class StatType(models.TextChoices):
        month = "month", _("Month")
        day = "day", _("Day")

    stat_type = models.CharField(max_length=10, choices=StatType.choices)
    stock = models.ForeignKey("general_service.Stock", on_delete=models.CASCADE, related_name="group_stats")

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
        unique_together = ["stat_type", "stock", "date"]
