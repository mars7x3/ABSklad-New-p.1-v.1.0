from django.contrib import admin
from .models import *


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('title', )
    list_display_links = ('title', )
    search_fields = ('title', )


class StockPhoneInline(admin.TabularInline):
    model = StockPhone
    max_num = 100
    extra = 0


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    inlines = [StockPhoneInline]
    search_fields = ('id', 'address', 'city__title')
    list_display = ('id', 'address', 'city')
    list_display_links = ('id', 'address', 'city')
