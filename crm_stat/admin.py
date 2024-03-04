from django.contrib import admin

from .models import StockGroupStat, UserTransactionsStat, PurchaseStat


@admin.register(UserTransactionsStat)
class UserTransactionsStatAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "date")
    search_fields = ("user__id",)
    list_filter = ("date",)
    list_per_page = 10
    list_max_show_all = 20


@admin.register(PurchaseStat)
class PurchaseStatAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'user', 'stock', 'date')
    search_fields = ('id', 'product__id', 'user__id', 'stock__id')
    list_filter = ('date',)
    list_per_page = 10
    list_max_show_all = 20


@admin.register(StockGroupStat)
class StockGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "stock", "stat_type", "date")
    list_filter = ("date", "stat_type")
    list_per_page = 10
    list_max_show_all = 20
