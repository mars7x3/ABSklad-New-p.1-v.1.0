from django.urls import path, re_path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

router.register('crm-kpi/dealer/crud', DealerKPIView)


urlpatterns = [
    path('crm/kpi/total/info/', KPITotalView.as_view()),
    path('crm/kpi/total/info/managers/', KPITotalMain2lvlView.as_view()),
    re_path("^crm/kpi/total/info/managers/(?P<manager_id>.+)/$", KPITotalMain3lvlView.as_view()),

    path('crm-kpi/tmz/list/', ManagerKPITMZView.as_view()),
    path('crm-kpi/tmz/detail/', ManagerKPITMZDetailView.as_view()),
    path('crm-kpi/pds/list/', ManagerKPIPDSListView.as_view()),
    path('crm-kpi/pds/detail/', ManagerKPIPDSDetailView.as_view()),

    path('', include(router.urls)),
]

