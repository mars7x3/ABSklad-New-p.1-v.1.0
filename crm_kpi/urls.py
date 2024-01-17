from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

router.register('crm-kpi/crud', DealerKPIView)
router.register('crm-kpi/tmz/bonus/crud', ManagerTMZBonusModelViewSet)
router.register('crm-kpi/pds/bonus/crud', ManagerPDSBonusModelViewSet)


urlpatterns = [
    path('crm-kpi/tmz/list/', ManagerKPITMZView.as_view()),
    path('crm-kpi/tmz/detail/', ManagerKPITMZDetailView.as_view()),
    path('crm-kpi/pds/list/', ManagerKPIPDSListView.as_view()),
    path('crm-kpi/pds/detail/', ManagerKPIPDSDetailView.as_view()),

    path('crm-kpi/manager/tmz/bonus/', ManagerTMZBonusView.as_view()),
    path('crm-kpi/manager/pds/bonus/', ManagerPDSBonusView.as_view()),
    path('', include(router.urls)),
]

