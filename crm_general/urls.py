from django.urls import path, re_path, include
from rest_framework.routers import SimpleRouter

from .manager.views import (
    OrderListAPIView, OrderRetrieveAPIView, OrderChangeActivityView, OrderCreateAPIView,
    DealerListViewSet, DealerBirthdayListAPIView, DealerRetrieveAPIView,
    DealerBalanceHistoryListAPIView, DealerBasketListAPIView,
    ProductPriceListAPIView, CollectionListAPIView, CategoryListAPIView, ProductRetrieveAPIView, BalanceViewSet,
    ReturnListAPIView, ReturnRetrieveAPIView, ReturnUpdateAPIView,
    BalancePlusManagerView
)

from .director.views import *
from .views import *

director_router = SimpleRouter()
director_router.register("director/staff/crud", StaffCRUDView)
director_router.register("director/product/detail", DirectorProductCRUDView)
director_router.register("director/discount/crud", DirectorDiscountCRUDView)
director_router.register("director/dealer/list", DirectorDealerListView)
director_router.register("director/dealer/crud", DirectorDealerCRUDView)


director_urlpatterns = [
    path("director/collection/list/", DirectorCollectionListView.as_view()),
    path("director/product/list/", DirectorProductListView.as_view()),
    path("director/balance/list/", BalanceListView.as_view()),
    path("director/balance/list/total/", BalanceListTotalView.as_view()),
    path("director/balance/history/list/", BalanceHistoryListView.as_view()),
    path("director/balance/history/total/", TotalEcoBalanceView.as_view()),
    path("director/collection/category/list/", CollectionCategoryListView.as_view()),
    path("director/collection/category/product/list/", CollectionCategoryProductListView.as_view()),
    path("director/discount/dealer-status/list/", DirectorDiscountDealerStatusView.as_view()),
    path("director/discount/city/list/", DirectorDiscountCityView.as_view()),
    path("director/discount/product/list/", DirectorDiscountAsiaProductView.as_view()),


    path("", include(director_router.urls)),
]

# --------------------------- MANAGER
manager_router = SimpleRouter()
manager_router.register("dealers", DealerListViewSet, basename="crm_general-manager-dealers")
manager_router.register("balances", BalanceViewSet, basename="crm_general-manager-balances")

manager_urlpatterns = [
    # Dealers
    path("manager/dealers/birthdays/", DealerBirthdayListAPIView.as_view(),
         name="crm_general-manager-dealers-birthdays-list"),
    re_path("^manager/dealers/(?P<user_id>.+)/detail/$", DealerRetrieveAPIView.as_view(),
            name="crm_general-manager-dealers-detail"),
    re_path("^manager/dealers/(?P<user_id>.+)/balance-history/$", DealerBalanceHistoryListAPIView.as_view(),
            name="crm_general-manager-dealers-balance-history-list"),
    re_path("^manager/dealers/(?P<user_id>.+)/basket-history/$", DealerBasketListAPIView.as_view(),
            name="crm_general-manager-dealers-basket-history-list"),
    # Orders
    path("manager/orders/", OrderListAPIView.as_view(), name="crm_general-manager-orders-list"),
    path("manager/orders/create/", OrderCreateAPIView.as_view(), name="crm_general-manager-orders-create"),
    re_path("^manager/orders/(?P<order_id>.+)/change-activity/$", OrderChangeActivityView.as_view(),
            name="crm_general-manager-orders-update-activity"),
    re_path("^manager/orders/(?P<order_id>.+)/detail/$", OrderRetrieveAPIView.as_view(),
            name="crm_general-manager-orders-detail"),
    # Products
    path("manager/collections/", CollectionListAPIView.as_view(), name="crm_general-manager-collections-list"),
    path("manager/categories/", CategoryListAPIView.as_view(), name="crm_general-manager-categories-list"),
    path("manager/products/", ProductPriceListAPIView.as_view(), name="crm_general-manager-products-list"),
    re_path("^manager/products/(?P<product_id>.+)/detail/$", ProductRetrieveAPIView.as_view(),
            name="crm_general-manager-product-detail"),
    # Returns
    path("manager/returns/", ReturnListAPIView.as_view(), name="crm_general-manager-returns-list"),
    re_path("^manager/returns/(?P<return_id>.+)/detail/$", ReturnRetrieveAPIView.as_view(),
            name="crm_general-manager-returns-detail"),
    re_path("^manager/returns/(?P<return_id>.+)/update/$", ReturnUpdateAPIView.as_view(),
            name="crm_general-manager-returns-update"),
    # Balances and Other
    path("manager/balance/plus/", BalancePlusManagerView.as_view(), name="crm_general-manager-balance-plus-create"),
    path("manager/", include(manager_router.urls)),
]

# --------------------------- ROP
rop_router = SimpleRouter()
# rop_router.register("managers", ManagerRopViewSet)


rop_urlpatterns = [
    path("rop/", include(rop_router.urls)),
]


crm_router = SimpleRouter()
crm_router.register("crm/collection/crud", CollectionCRUDView)


crm_urlpatterns = [
    path("crm/product/images/create/", ProductImagesCreate.as_view()),
    path("crm/city/list/", CityListView.as_view()),
    path("crm/stock/list/", StockListView.as_view()),
    path("crm/user/image/cd", UserImageCDView.as_view()),


    path("", include(crm_router.urls)),
]


# + some_urlpatterns
urlpatterns = manager_urlpatterns + rop_urlpatterns + director_urlpatterns + crm_urlpatterns
