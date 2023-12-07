from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register('dealer/stories', StoriesListView)
router.register('dealer/target/list', TargetListView)

urlpatterns = [
    path('', include(router.urls)),
]
