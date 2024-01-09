from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

urlpatterns = [

    path('crm/sync/1c-to-crm/', SyncProductCRUDVIew.as_view()),

    path('', include(router.urls)),
]