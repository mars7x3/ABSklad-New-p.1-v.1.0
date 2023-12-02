from django.contrib import admin
from .models import *


class CartProductInline(admin.TabularInline):
    model = CartProduct
    max_num = 100
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    inlines = [CartProductInline]