from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from .views import *

from one_c import task_views

router = DefaultRouter()

notifications_urlpatterns = [
    path('crm/notifications/', task_views.tasks_list_view, name="one-c-tasks-list"),
    re_path("^crm/notifications/(?P<task_key>.+)/detail/$", task_views.task_detail_view, name="one-c-tasks-detail"),
    re_path("^crm/notifications/(?P<task_key>.+)/remove/$", task_views.task_destroy_view, name="one-c-tasks-destroy"),
    re_path("^crm/notifications/(?P<task_key>.+)/repeat/$", task_views.task_repeat_view, name="one-c-tasks-repeat"),
]

urlpatterns = [
    path('crm/sync/1c-to-crm/', SyncProductCRUDView.as_view()),  # product crud
    path('crm/1c/sync/category/', SyncCategoryCRUDView.as_view()),  # category crud
    path('crm/sync/dealer/1c-to-crm/', SyncDealerCRUDView.as_view()),  # dealer crud
    path('crm/1c/sync/order/', SyncOrderCRUDView.as_view()),  # order crud
    path('crm/1c/sync/balance/', SyncMoneyDocCRUDView.as_view()),  # money-doc crud
    path('crm/1c/sync/price-type/', SyncPriceTypeCRUDView.as_view()),  # price-type crud
    path('crm/1c/sync/user-city/', SyncUserCityCRUDView.as_view()),  # user-city crud
    path('crm/1c/sync/stock/', SyncStockCRUDView.as_view()),  # stock crud
    path('crm/1c/sync/prod/count/', SyncProdCountCRUDView.as_view()),  # prod count crud
    path('crm/1c/sync/prod/price/', SyncProdPriceCRUDView.as_view()),  # prod price crud
    path('crm/1c/sync/inventory/', SyncInventoryCRUDView.as_view()),
    path('crm/1c/sync/movement/', SyncMovementCRUDView.as_view()),
    path('crm/1c/sync/return/', SyncReturnCRUDView.as_view()),

    path('', include(router.urls)),
] + notifications_urlpatterns

"""
list - /api/v1/crm/notifications/
detail - /api/v1/crm/notifications/<task_key>/detail/
delete - /api/v1/crm/notifications/<task_key>/remove/
repeat - /api/v1/crm/notifications/<task_key>/repeat/
"""
