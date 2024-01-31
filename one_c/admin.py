from django.contrib import admin

from .models import *


admin.site.register(MoneyDoc)


class MovementProductInline(admin.TabularInline):
    model = MovementProducts
    max_num = 1000
    extra = 0


@admin.register(MovementProduct1C)
class MovementProduct1CAdmin(admin.ModelAdmin):
    inlines = [MovementProductInline]
