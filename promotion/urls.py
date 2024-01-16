from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register('dealer/stories', StoriesListView)
router.register('dealer/banners', BannerListView)


urlpatterns = [
    path('dealer/motivation/list/', MotivationView.as_view()),  # motivation list
    path('dealer/kpi/info/', KPIInfoView.as_view()),
    path('dealer/kpi/products/', KPIProductsView.as_view()),

    path('kpi/tmz/count/', ManagerKPITMZView.as_view()),

    path('', include(router.urls)),
]

