from django.urls import path, re_path, include
from rest_framework.routers import SimpleRouter

from .manager.views import (
    DealerManagerViewSet, OrderManagerViewSet,
    CategoryManagerView, CategoryProductsManagerView, ProductRetrieveManagerView,
    BalanceHistoryManagerViewSet, BalancePlusManagerView, WalletManagerViewSet, OrderManagerCreateView,
    ManagerStockView
)
from .rop.views import (
    ManagerRopViewSet
)

manager_router = SimpleRouter()
manager_router.register("dealers", DealerManagerViewSet)
manager_router.register("warehouses", WalletManagerViewSet)
manager_router.register("orders", OrderManagerViewSet)
manager_router.register('balances', WalletManagerViewSet)
manager_router.register('balance/plus', BalanceHistoryManagerViewSet)

manager_urlpatterns = [
    path('manager/stocks/', ManagerStockView.as_view(), name='crm_general-manager-stocks-list'),
    path('manager/categories/', CategoryManagerView.as_view(), name='crm_general-manager-categories-list'),
    re_path('^manager/categories/(?P<category_slug>.+)/products/$', CategoryProductsManagerView.as_view(),
            name='crm_general-manager-category-products-list'),
    re_path('^manager/products/(?P<product_id>.+)/detail$', ProductRetrieveManagerView.as_view(),
            name="crm_general-manager-products-retrieve"),
    path('manager/balance/plus/', BalancePlusManagerView.as_view(), name="crm_general-manager-dealer-balance-plus"),
    path('manager/', include(manager_router.urls)),
    path('manager/order/create/', OrderManagerCreateView.as_view(), name="crm_general-manager-order-create"),
]

rop_router = SimpleRouter()
rop_router.register("managers", ManagerRopViewSet)


rop_urlpatterns = [
    path('rop/', include(rop_router.urls)),
]

# + some_urlpatterns
urlpatterns = manager_urlpatterns + rop_urlpatterns
