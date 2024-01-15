from django.contrib import admin
from .models import *


class CartProductInline(admin.TabularInline):
    model = CartProduct
    max_num = 100
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    inlines = [CartProductInline]


class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    max_num = 100
    extra = 0


class OrderReceiptInline(admin.TabularInline):
    model = OrderReceipt
    max_num = 100
    extra = 0


@admin.register(MyOrder)
class MyOrderAdmin(admin.ModelAdmin):
    inlines = [OrderProductInline, OrderReceiptInline]


class ReturnOrderProductInline(admin.StackedInline):
    model = ReturnOrderProduct
    extra = 0


@admin.register(ReturnOrder)
class ReturnOrderAdmin(admin.ModelAdmin):
    inlines = (ReturnOrderProductInline,)


admin.site.register(OrderReceipt)
