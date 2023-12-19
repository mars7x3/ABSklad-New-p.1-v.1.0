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

from .director.views import *
from .views import *

director_router = SimpleRouter()
director_router.register("director/staff/crud", StaffCRUDView)
director_router.register("director/product/detail", DirectorProductCRUDView)
director_router.register("director/discount/crud", DirectorDiscountCRUDView)
director_router.register("director/dealer/list", DirectorDealerListStatusView)

director_urlpatterns = [
    path("director/collection/list/", DirectorCollectionListView.as_view()),
    path("director/product/list/", DirectorProductListView.as_view()),
    path("director/balance/list/", BalanceListView.as_view()),
    path('director/balance/list/total/', BalanceListTotalView.as_view()),
    path('director/balance/history/list/', BalanceHistoryListView.as_view()),
    path('director/balance/history/total/', TotalEcoBalanceView.as_view()),
    path('director/collection/category/list/', CollectionCategoryListView.as_view()),
    path('director/collection/category/product/list/', CollectionCategoryProductListView.as_view()),
    path('director/discount/dealer-status/list/', DirectorDiscountDealerStatusView.as_view()),
    path('director/discount/city/list/', DirectorDiscountCityView.as_view()),
    path('director/discount/product/list/', DirectorDiscountAsiaProductView.as_view()),


    path('', include(director_router.urls)),
]

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


crm_router = SimpleRouter()
crm_router.register("crm/collection/crud", CollectionCRUDView)


crm_urlpatterns = [
    path('crm/product/images/create/', ProductImagesCreate.as_view()),
    path("crm/city/list/", CityListView.as_view()),
    path("crm/stock/list/", StockListView.as_view()),
    path('', include(crm_router.urls)),
]


# + some_urlpatterns
urlpatterns = manager_urlpatterns + rop_urlpatterns + director_urlpatterns + crm_urlpatterns


