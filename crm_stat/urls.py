from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import PDSByCityView, SalesByCityView, LimitOffsetView, PDSByCityDetail


router = SimpleRouter()

urlpatterns = [
    path('crm-stats/pds/city/', PDSByCityView.as_view()),
    path('crm-stats/pds/city/detail/', PDSByCityDetail.as_view()),
    path('crm-stats/sales/city/', SalesByCityView.as_view()),
    path('crm-stats/pagination/', LimitOffsetView.as_view()),
    path('crm-stats/', include(router.urls)),

]
