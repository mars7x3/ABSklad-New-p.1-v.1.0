from django.contrib import admin

from crm_general.models import *

admin.site.register(CRMTask)

admin.site.register(KPI)
admin.site.register(KPIItem)

admin.site.register(Inventory)
admin.site.register(InventoryProduct)


admin.site.register(DealerKPIPlan)
admin.site.register(DealerKPIPlanStat)
admin.site.register(ProductToBuy)
admin.site.register(CityProductToBuy)
admin.site.register(CityProductToBuyStat)
admin.site.register(ProductRecommendation)
