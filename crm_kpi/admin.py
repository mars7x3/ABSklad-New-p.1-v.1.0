from django.contrib import admin

from crm_kpi.models import DealerKPIProduct, DealerKPI, ManagerKPIPDSInfo, ManagerKPITMZInfo


class DealerKPIProductInline(admin.TabularInline):
    model = DealerKPIProduct
    max_num = 1000
    extra = 0


@admin.register(DealerKPI)
class DealerKPIAdmin(admin.ModelAdmin):
    inlines = [DealerKPIProductInline]


admin.site.register(ManagerKPIPDSInfo)
admin.site.register(ManagerKPITMZInfo)
