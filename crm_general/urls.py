from django.urls import path, re_path, include
from rest_framework.routers import SimpleRouter

from .manager.views import (
    OrderListAPIView as ManagerOrderListView,
    OrderRetrieveAPIView as ManagerOrderRetrieveView,
    OrderChangeActivityView as ManagerOrderChangeActivityView,
    OrderCreateAPIView as ManagerOrderCreateAPIView,
    DealerListViewSet as ManagerDealerListViewSet,
    DealerCreateAPIView as ManagerDealerCreateAPIView,
    DealerBirthdayListAPIView as ManagerDealerBirthdayListAPIView,
    DealerRetrieveAPIView as ManagerDealerRetrieveAPIView,
    DealerBalanceHistoryListAPIView as ManagerDealerBalanceHistoryListAPIView,
    DealerBasketListAPIView as ManagerDealerBasketListAPIView,
    ProductPriceListAPIView as ManagerProductPriceListAPIView,
    CollectionListAPIView as ManagerCollectionListAPIView,
    CategoryListAPIView as ManagerCategoryListAPIView,
    ProductRetrieveAPIView as ManagerProductRetrieveAPIView,
    BalanceViewSet as ManagerBalanceViewSet,
    ReturnListAPIView as ManagerReturnListAPIView,
    ReturnRetrieveAPIView as ManagerReturnRetrieveAPIView,
    ReturnUpdateAPIView as ManagerReturnUpdateAPIView,
    BalancePlusManagerView as ManagerBalancePlusManagerView
)

from .rop.views import (
    ManagerListAPIView as RopManagerListAPIView,
    ManagerRetrieveAPIView as RopManagerRetrieveAPIView,
    ManagerCreateAPIView as RopManagerCreateAPIView,
    DealerListViewSet as RopDealerListViewSet,
    DealerRetrieveAPIView as RopDealerRetrieveAPIView,
    DealerBalanceHistoryListAPIView as RopDealerBalanceHistoryListAPIView,
    DealerBasketListAPIView as RopDealerBasketListAPIView,
    DealerStatusListAPIView as RopDealerStatusListAPIView,
    DealerStatusCreateAPIView as RopDealerStatusCreateAPIView,
    DealerStatusUpdateAPIView as RopDealerStatusUpdateAPIView,
    CollectionListAPIView as RopCollectionListAPIView,
    CategoryListAPIView as RopCategoryListAPIView,
    ProductPriceListAPIView as RopProductPriceListAPIView,
    ProductRetrieveAPIView as RopProductRetrieveAPIView,
    BalanceViewSet as BalanceViewSet
)

from .director.views import *
from .views import *

from .marketer.views import (
    MarketerProductRUViewSet, MarketerCollectionModelViewSet, MarketerCategoryModelViewSet, ProductSizeView,
    MarketerBannerModelViewSet, MarketerStoryViewSet, CRMNotificationView, MarketerDealerStatusListView,
)
from .warehouse_manager.views import (
    WareHouseOrderView, WareHouseCollectionViewSet, WareHouseProductViewSet, WareHouseCategoryViewSet,
    WareHouseSaleReportView
)

director_router = SimpleRouter()
director_router.register("director/staff/crud", StaffCRUDView)
director_router.register("director/product/detail", DirectorProductCRUDView)
director_router.register("director/discount/crud", DirectorDiscountCRUDView)
director_router.register("director/dealer/list", DirectorDealerListView)
director_router.register("director/dealer/crud", DirectorDealerCRUDView)
director_router.register("director/motivation/crud", DirectorMotivationCRUDView)
director_router.register("director/motivation/list", DirectorMotivationListView)
director_router.register("director/motivation/dealer/list", DirectorMotivationDealerListView)
director_router.register("director/product/list", DirectorProductListView)
director_router.register("director/balance/list", BalanceListView)
director_router.register("director/discount/product/list", DirectorDiscountAsiaProductView)
director_router.register("director/price/list", DirectorPriceListView)
director_router.register("director/task/crud", DirectorTaskCRUDView)
director_router.register("director/task/list", DirectorTaskListView)
director_router.register("director/grade/crud", DirectorGradeCRUDView)
director_router.register("director/staff/list", DirectorStaffListView)
director_router.register("director/stock/crud", DirectorStockCRUDView)
director_router.register("director/stock/list", DirectorStockListView)
director_router.register("director/stock/product/list", DStockProductListView)

director_urlpatterns = [
    path("director/collection/list/", DirectorCollectionListView.as_view()),
    path('director/balance/list/total/', BalanceListTotalView.as_view()),
    path('director/balance/history/list/', BalanceHistoryListView.as_view()),
    path('director/balance/history/total/', TotalEcoBalanceView.as_view()),
    path('director/collection/category/list/', CollectionCategoryListView.as_view()),
    path('director/collection/category/product/list/', CollectionCategoryProductListView.as_view()),
    path('director/discount/dealer-status/list/', DirectorDiscountDealerStatusView.as_view()),
    path('director/discount/city/list/', DirectorDiscountCityView.as_view()),
    path('director/dealer/order/list/', DirectorDealerOrderListView.as_view()),
    path('director/dealer/cart/list/', DirectorDealerCartListView.as_view()),
    path('director/dealer/balance-history/list/', DirectorBalanceHistoryListView.as_view()),
    path('director/dealer/total-amounts/', DirectorTotalAmountView.as_view()),
    path('director/price/create/', DirectorPriceCreateView.as_view()),
    path('director/task/grade/', DirectorGradeView.as_view()),

    path('', include(director_router.urls)),
]

# --------------------------- MANAGER
manager_router = SimpleRouter()
manager_router.register("dealers", ManagerDealerListViewSet, basename="crm_general-manager-dealers")
manager_router.register("balances", ManagerBalanceViewSet, basename="crm_general-manager-balances")

manager_urlpatterns = [
    # Dealers
    path("manager/dealers/create/", ManagerDealerCreateAPIView.as_view(), name="crm_general-manager-dealers-create"),
    path("manager/dealers/birthdays/", ManagerDealerBirthdayListAPIView.as_view(),
         name="crm_general-manager-dealers-birthdays-list"),
    re_path("^manager/dealers/(?P<user_id>.+)/detail/$", ManagerDealerRetrieveAPIView.as_view(),
            name="crm_general-manager-dealers-detail"),
    re_path("^manager/dealers/(?P<user_id>.+)/balance-history/$", ManagerDealerBalanceHistoryListAPIView.as_view(),
            name="crm_general-manager-dealers-balance-history-list"),
    re_path("^manager/dealers/(?P<user_id>.+)/basket-history/$", ManagerDealerBasketListAPIView.as_view(),
            name="crm_general-manager-dealers-basket-history-list"),
    # Orders
    path("manager/orders/", ManagerOrderListView.as_view(), name="crm_general-manager-orders-list"),
    path("manager/orders/create/", ManagerOrderCreateAPIView.as_view(), name="crm_general-manager-orders-create"),
    re_path("^manager/orders/(?P<order_id>.+)/change-activity/$", ManagerOrderChangeActivityView.as_view(),
            name="crm_general-manager-orders-update-activity"),
    re_path("^manager/orders/(?P<order_id>.+)/detail/$", ManagerOrderRetrieveView.as_view(),
            name="crm_general-manager-orders-detail"),
    # Products
    path("manager/collections/", ManagerCollectionListAPIView.as_view(), name="crm_general-manager-collections-list"),
    path("manager/categories/", ManagerCategoryListAPIView.as_view(), name="crm_general-manager-categories-list"),
    path("manager/products/", ManagerProductPriceListAPIView.as_view(), name="crm_general-manager-products-list"),
    re_path("^manager/products/(?P<product_id>.+)/detail/$", ManagerProductRetrieveAPIView.as_view(),
            name="crm_general-manager-product-detail"),
    # Returns
    path("manager/returns/", ManagerReturnListAPIView.as_view(), name="crm_general-manager-returns-list"),
    re_path("^manager/returns/(?P<return_id>.+)/detail/$", ManagerReturnRetrieveAPIView.as_view(),
            name="crm_general-manager-returns-detail"),
    re_path("^manager/returns/(?P<return_id>.+)/update/$", ManagerReturnUpdateAPIView.as_view(),
            name="crm_general-manager-returns-update"),
    # Balances and Other
    path("manager/balance/plus/", ManagerBalancePlusManagerView.as_view(),
         name="crm_general-manager-balance-plus-create"),
    path("manager/", include(manager_router.urls)),
]

# --------------------------- ROP
rop_router = SimpleRouter()
rop_router.register("dealers", RopDealerListViewSet, basename="crm_general-rop-dealers")
rop_router.register("balances", BalanceViewSet, basename="crm_general-rop-balances")

rop_urlpatterns = [
    # Managers
    path("rop/managers/", RopManagerListAPIView.as_view(), name="crm_general-rop-managers-list"),
    path("rop/managers/create/", RopManagerCreateAPIView.as_view(), name="crm_general-rop-managers-create"),
    re_path(r"^rop/managers/(?P<user_id>.+)/detail/$", RopManagerRetrieveAPIView.as_view(),
            name="crm_general-rop-managers-detail"),

    # Dealers
    re_path("^rop/dealers/(?P<user_id>.+)/detail/$", RopDealerRetrieveAPIView.as_view(),
            name="crm_general-rop-dealers-detail"),
    re_path("^rop/dealers/(?P<user_id>.+)/balance-history/$", RopDealerBalanceHistoryListAPIView.as_view(),
            name="crm_general-rop-dealers-balance-history-list"),
    re_path("^rop/dealers/(?P<user_id>.+)/basket-history/$", RopDealerBasketListAPIView.as_view(),
            name="crm_general-rop-dealers-basket-history-list"),
    path("rop/dealer-statuses/", RopDealerStatusListAPIView.as_view(), name="crm_general-rop-dealer-status-list"),
    path("rop/dealer-status/create/", RopDealerStatusCreateAPIView.as_view(),
         name="crm_general-rop-dealer-status-create"),
    re_path("^rop/dealer-status/(?P<status_id>.+)/update/$", RopDealerStatusUpdateAPIView.as_view(),
            name="crm_general-rop-dealer-status-update"),

    # Products
    path("rop/collections/", RopCollectionListAPIView.as_view(), name="crm_general-rop-collections-list"),
    path("rop/categories/", RopCategoryListAPIView.as_view(), name="crm_general-rop-categories-list"),
    path("rop/products/", RopProductPriceListAPIView.as_view(), name="crm_general-rop-products-list"),
    re_path("^rop/products/(?P<product_id>.+)/detail/$", RopProductRetrieveAPIView.as_view(),
            name="crm_general-rop-product-detail"),

    path("rop/", include(rop_router.urls)),
]
# ---------------------------

marketer_router = SimpleRouter()
marketer_router.register('product', MarketerProductRUViewSet)
marketer_router.register('collection', MarketerCollectionModelViewSet)
marketer_router.register('category', MarketerCategoryModelViewSet)
marketer_router.register('banner', MarketerBannerModelViewSet)
marketer_router.register('story', MarketerStoryViewSet)
marketer_router.register('crm-notification', CRMNotificationView)
marketer_router.register('product-size', ProductSizeView)

marketer_urlpatterns = [
    path('marketer/dealer-status/list/', MarketerDealerStatusListView.as_view({'get': 'list'})),
    path('marketer/', include(marketer_router.urls)),
]


warehouse_manager_router = SimpleRouter()
warehouse_manager_router.register('order', WareHouseOrderView, basename='warehouse-order')
warehouse_manager_router.register('product', WareHouseProductViewSet, basename='warehouse-product')
warehouse_manager_router.register('category', WareHouseCategoryViewSet, basename='warehouse-category')
warehouse_manager_router.register('collection', WareHouseCollectionViewSet, basename='warehouse-collection')

warehouse_manager_urlpatterns = [
    path('warehouse-manager/', include(warehouse_manager_router.urls)),
    path('warehouse-manager/report/', WareHouseSaleReportView.as_view()),
]

crm_router = SimpleRouter()
crm_router.register("crm/collection/crud", CollectionCRUDView)
crm_router.register("crm/category/crud", CategoryCRUDView)
crm_router.register("crm/dealer-status/list", DealerStatusListView)

crm_urlpatterns = [
    path("crm/product/images/create/", ProductImagesCreate.as_view()),
    path("crm/city/list/", CityListView.as_view()),
    path("crm/stock/list/", StockListView.as_view()),
    path("crm/category/list/", CategoryListView.as_view()),


    path("crm/user/image/cd", UserImageCDView.as_view()),

    path("", include(crm_router.urls)),
]

# + some_urlpatterns
urlpatterns = (manager_urlpatterns + rop_urlpatterns + director_urlpatterns + crm_urlpatterns + marketer_urlpatterns +
               warehouse_manager_urlpatterns)
