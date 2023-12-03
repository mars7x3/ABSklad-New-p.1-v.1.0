from django.urls import path, re_path, include
from rest_framework.routers import SimpleRouter

from crm_manager.views import DealerViewSet, WareHouseViewSet

router = SimpleRouter()
router.register("dealers", DealerViewSet)
router.register("warehouses", WareHouseViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
