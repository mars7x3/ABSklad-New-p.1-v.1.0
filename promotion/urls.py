from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register('dealer/stories', StoriesListView)
router.register('dealer/banners', BannerListView)


urlpatterns = [

    path('dealer/motivation/list/', MotivationView.as_view()),  # motivation list

    path('', include(router.urls)),
]

