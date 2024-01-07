from django.contrib import admin

from crm_general.models import *

admin.site.register(CRMTaskGrade)
admin.site.register(CRMTask)

admin.site.register(KPI)
admin.site.register(KPIItem)

admin.site.register(CRMTaskResponse)
admin.site.register(CRMTaskResponseFile)
admin.site.register(Inventory)
admin.site.register(InventoryProduct)


admin.site.register(DealerKPIPlan)
admin.site.register(ProductToBuy)
admin.site.register(ProductToBuyCount)
