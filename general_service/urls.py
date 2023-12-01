from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

router.register('dealer/stock/list', CategoryListView)
router.register('dealer/city/list', CityListView)


urlpatterns = [
    path('', include(router.urls)),
]