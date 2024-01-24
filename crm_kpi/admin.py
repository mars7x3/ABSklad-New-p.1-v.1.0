from django.contrib import admin
from .models import DealerKPI, DealerKPIProduct, ManagerKPI, ManagerKPISVD, ManagerKPIInfo


class DealerKPIProductAdmin(admin.TabularInline):
    model = DealerKPIProduct
    max_num = 1000
    extra = 0


@admin.register(DealerKPI)
class DealerKPIAdmin(admin.ModelAdmin):
    inlines = [DealerKPIProductAdmin]


class MangerKPISVDAdmin(admin.TabularInline):
    model = ManagerKPISVD
    max_num = 1000
    extra = 0


class MangerKPITMZAdmin(admin.TabularInline):
    model = ManagerKPIInfo
    max_num = 1000
    extra = 0


@admin.register(ManagerKPI)
class DealerKPIAdmin(admin.ModelAdmin):
    inlines = [MangerKPITMZAdmin, MangerKPISVDAdmin]
