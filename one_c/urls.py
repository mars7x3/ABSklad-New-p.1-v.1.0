from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

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
    path('crm/1c/sync/movement/', SyncProdPriceCRUDView.as_view()),
    path('crm/1c/sync/return/', SyncProdPriceCRUDView.as_view()),

    path('', include(router.urls)),
]