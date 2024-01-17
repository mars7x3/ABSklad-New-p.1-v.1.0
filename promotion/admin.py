from django.contrib import admin

from .models import *

admin.site.register(Story)
admin.site.register(Discount)
admin.site.register(Motivation)
admin.site.register(Banner)


class ConditionCategoryInline(admin.TabularInline):
    model = ConditionCategory
    max_num = 1000
    extra = 0


class ConditionProductInline(admin.TabularInline):
    model = ConditionProduct
    max_num = 1000
    extra = 0


class MotivationPresentInline(admin.TabularInline):
    model = MotivationPresent
    max_num = 1000
    extra = 0


@admin.register(MotivationCondition)
class MotivationConditionAdmin(admin.ModelAdmin):
    inlines = [MotivationPresentInline, ConditionCategoryInline, ConditionProductInline]
    search_fields = ('id', 'title')
    list_display = ('id', 'status', 'motivation')
    list_display_links = ('id', 'status', 'motivation')

