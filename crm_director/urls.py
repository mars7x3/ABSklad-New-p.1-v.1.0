from django.urls import path, include
from rest_framework.routers import DefaultRouter
from crm_director.views import *


router = DefaultRouter()

router.register("director/staff/crud", StaffCRUDView)

router.register("director/stock/crud", StockCRUDView)

urlpatterns = [

    path('', include(router.urls)),
]
