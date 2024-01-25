from django.urls import path, re_path, include
from rest_framework.routers import SimpleRouter

from .accountant.views import AccountantOrderListView, AccountantProductListView, AccountantCollectionListView, \
    AccountantCategoryView, AccountantStockViewSet
from .hr.views import HRStaffListView, StaffMagazineCreateView
from .main_director.views import MainDirStaffCRUDView, MainDirectorStockListView

from .manager.views import (
    OrderListAPIView as ManagerOrderListView,
    OrderRetrieveAPIView as ManagerOrderRetrieveView,
    OrderChangeActivityView as ManagerOrderChangeActivityView,
    OrderCreateAPIView as ManagerOrderCreateAPIView,
    DealerListViewSet as ManagerDealerListViewSet,
    DealerCreateAPIView as ManagerDealerCreateAPIView,
    DealerUpdateAPIView as ManagerDealerUpdateAPIView,
    DealerChangeActivityView as ManagerDealerChangeActivityView,
    DealerImageUpdateAPIView as ManagerDealerImageUpdateAPIView,
    DealerBirthdayListAPIView as ManagerDealerBirthdayListAPIView,
    DealerRetrieveAPIView as ManagerDealerRetrieveAPIView,
    DealerBalanceHistoryListAPIView as ManagerDealerBalanceHistoryListAPIView,
    DealerBasketListAPIView as ManagerDealerBasketListAPIView,
    ProductPriceListAPIView as ManagerProductPriceListAPIView,
    CollectionListAPIView as ManagerCollectionListAPIView,
    CategoryListAPIView as ManagerCategoryListAPIView,
    ProductRetrieveAPIView as ManagerProductRetrieveAPIView,
    BalanceViewSet as ManagerBalanceViewSet,
    BalancePlusManagerView as ManagerBalancePlusManagerView, ProdListForOrderView, ManagerDeleteOrderView,
)

from .rop.views import (
    ManagerListAPIView as RopManagerListAPIView,
    ManagerRetrieveAPIView as RopManagerRetrieveAPIView,
    ManagerCreateAPIView as RopManagerCreateAPIView,
    ManagerUpdateAPIView as RopManagerUpdateAPIView,
    ManagerChangeActivityView as RopManagerChangeActivityView,
    ManagerImageUpdateAPIView as RopManagerImageUpdateAPIView,
    DealerListViewSet as RopDealerListViewSet,
    DealerRetrieveAPIView as RopDealerRetrieveAPIView,
    DealerBalanceHistoryListAPIView as RopDealerBalanceHistoryListAPIView,
    DealerBasketListAPIView as RopDealerBasketListAPIView,
    DealerCreateAPIView as RopDealerCreateAPIView,
    DealerUpdateAPIView as RopDealerUpdateAPIView,
    DealerImageUpdateAPIView as RopDealerImageUpdateAPIView,
    DealerChangeActivityView as RopDealerChangeActivityView,
    DealerStatusListAPIView as RopDealerStatusListAPIView,
    DealerStatusCreateAPIView as RopDealerStatusCreateAPIView,
    DealerStatusUpdateAPIView as RopDealerStatusUpdateAPIView,
    CollectionListAPIView as RopCollectionListAPIView,
    CategoryListAPIView as RopCategoryListAPIView,
    ProductPriceListAPIView as RopProductPriceListAPIView,
    ProductRetrieveAPIView as RopProductRetrieveAPIView,
    BalanceViewSet as BalanceViewSet,
    ManagerShortListView as ManagerShortListView
)

from .director.views import *
from .accountant.views import *

from .views import *

from .marketer.views import (
    MarketerProductRUViewSet, MarketerCollectionModelViewSet, MarketerCategoryModelViewSet, ProductSizeView,
    MarketerBannerModelViewSet, MarketerStoryViewSet, CRMNotificationView, MarketerDealerStatusListView,
    MarketerProductHitsListView,
)
from .warehouse_manager.views import (
    WareHouseOrderView, WareHouseCollectionViewSet, WareHouseProductViewSet, WareHouseCategoryViewSet,
    WareHouseSaleReportView, WareHouseInventoryView, WareHouseSaleReportDetailView, ReturnOrderProductView,
    InventoryProductDeleteView
)

main_director_router = SimpleRouter()

main_director_router.register('staff/crud', MainDirStaffCRUDView)
main_director_router.register('stock/list', MainDirectorStockListView)

main_director_urlpatterns = [

    path('main_director/', include(main_director_router.urls)),
]


hr_router = SimpleRouter()
hr_router.register("hr/staff/list", HRStaffListView)
hr_router.register("hr/magazine/create", StaffMagazineCreateView)

hr_urlpatterns = [

    path('', include(hr_router.urls)),
]


director_router = SimpleRouter()
director_router.register("director/staff/crud", StaffCRUDView)
director_router.register("director/product/detail", DirectorProductCRUDView)
director_router.register("director/discount/crud", DirectorDiscountCRUDView)
director_router.register("director/dealer/list", DirectorDealerListView)
director_router.register("director/dealer/crud", DirectorDealerCRUDView)
# director_router.register("director/motivation/crud", DirectorMotivationCRUDView)
# director_router.register("director/motivation/list", DirectorMotivationListView)
# director_router.register("director/motivation/dealer/list", DirectorMotivationDealerListView)
director_router.register("director/product/list", DirectorProductListView)
director_router.register("director/balance/list", BalanceListView)
director_router.register("director/discount/product/list", DirectorDiscountAsiaProductView)
director_router.register("director/price/list", DirectorPriceListView)
director_router.register("director/task/crud", DirectorTaskCRUDView)
director_router.register("director/task/list", DirectorTaskListView)
director_router.register("director/staff/list", DirectorStaffListView)
director_router.register("director/stock/crud", DirectorStockCRUDView)
director_router.register("director/stock/list", DirectorStockListView)
director_router.register("director/stock/product/list", DStockProductListView)
# director_router.register("director/kpi/crud", DirectorKPICRUDView)
# director_router.register("director/kpi/list", DirectorKPIListView)
director_router.register("director/price-type/crud", PriceTypeCRUDView)
director_router.register("director/dealer-status/crud", DealerStatusModelViewSet)
director_router.register("director/category/crud", DirectorCategoryModelViewSet)


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
    path('director/price-type/create/', DirectorPriceTypeCreateView.as_view()),
    path('director/price-city/create/', DirectorPriceCityCreateView.as_view()),
    path('director/task/total-info/', DirectorTaskTotalInfoView.as_view()),
    path('director/free/warehouses/list/', DirFreeMainWarehouseListView.as_view()),
    path('director/warehouses/add-to-stock/', DirJoinWarehouseToStockListView.as_view()),
    path('director/rop/deactivate/', ROPChangeView.as_view()),
    path('director/warehouse/deactivate/', WareHouseChangeView.as_view()),

    path('max-test/', MaxatTestView.as_view()),


    path('', include(director_router.urls)),
]

# --------------------------- ACCOUNTANT
accountant_router = SimpleRouter()
accountant_router.register("accountant/order/list", AccountantOrderListView)
accountant_router.register("accountant/product/list", AccountantProductListView)
accountant_router.register("accountant/collection/list", AccountantCollectionListView)
accountant_router.register("accountant/category/list", AccountantCategoryView)
accountant_router.register("accountant/stock/list", AccountantStockViewSet)
accountant_router.register("accountant/balance/list", AccountantBalanceListView)
accountant_router.register("accountant/balance/plus/list", BalancePlusListView)
accountant_router.register("accountant/inventory", InventoryListUpdateView)
accountant_router.register("accountant/return-order", ReturnOrderView)
accountant_router.register("accountant/return-order/update", ReturnOrderProductUpdateView)


accountant_urlpatterns = [
    path('accountant/order/total-info/', AccountantOrderTotalInfoView.as_view()),
    path('accountant/balance/history/list/', AccountantBalanceHistoryListView.as_view()),
    path('accountant/balance/history/total/', AccountantTotalEcoBalanceView.as_view()),
    path('accountant/balance/plus/moderation/', BalancePlusModerationView.as_view()),
    path('accountant/order/moderation/paid/', AccountantOrderModerationView.as_view()),

    path('', include(accountant_router.urls)),
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
    re_path("^manager/dealers/(?P<user_id>.+)/update/$", ManagerDealerUpdateAPIView.as_view(),
            name="crm_general-manager-dealers-update"),
    re_path("^manager/dealers/(?P<user_id>.+)/update-image/$", ManagerDealerImageUpdateAPIView.as_view(),
            name="crm_general-manager-dealers-update-image"),
    re_path("^manager/dealers/(?P<user_id>.+)/balance-history/$", ManagerDealerBalanceHistoryListAPIView.as_view(),
            name="crm_general-manager-dealers-balance-history-list"),
    re_path("^manager/dealers/(?P<user_id>.+)/basket-history/$", ManagerDealerBasketListAPIView.as_view(),
            name="crm_general-manager-dealers-basket-history-list"),
    re_path("^manager/dealers/(?P<user_id>.+)/change-activity/$", ManagerDealerChangeActivityView.as_view(),
            name="crm_general-manager-dealers-update-activity"),
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

    # Balances and Other
    path("manager/balance/plus/", ManagerBalancePlusManagerView.as_view(),
         name="crm_general-manager-balance-plus-create"),
    path("manager/product/list/for-order/", ProdListForOrderView.as_view()),
    path("manager/order/delete", ManagerDeleteOrderView.as_view()),

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

    re_path("^rop/managers/(?P<user_id>.+)/update/$", RopManagerUpdateAPIView.as_view(),
            name="crm_general-rop-managers-update"),
    re_path("^rop/managers/(?P<user_id>.+)/update-image/$", RopManagerImageUpdateAPIView.as_view(),
            name="crm_general-rop-managers-update-image"),
    re_path("^rop/managers/(?P<user_id>.+)/change-activity/$", RopManagerChangeActivityView.as_view(),
            name="crm_general-manager-managers-update-activity"),

    re_path(r"^rop/managers/(?P<user_id>.+)/detail/$", RopManagerRetrieveAPIView.as_view(),
            name="crm_general-rop-managers-detail"),

    # Dealers
    path("rop/dealers/create/", RopDealerCreateAPIView.as_view(), name="crm_general-rop-dealers-create"),

    re_path("^rop/dealers/(?P<user_id>.+)/update/$", RopDealerUpdateAPIView.as_view(),
            name="crm_general-rop-dealers-update"),
    re_path("^rop/dealers/(?P<user_id>.+)/update-image/$", RopDealerImageUpdateAPIView.as_view(),
            name="crm_general-rop-dealers-update-image"),
    re_path("^rop/dealers/(?P<user_id>.+)/change-activity/$", RopDealerChangeActivityView.as_view(),
            name="crm_general-manager-dealers-update-activity"),

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

    # Tasks
    path("rop/", include(rop_router.urls)),
]
# --------------------------- MARKETER

marketer_router = SimpleRouter()
marketer_router.register('product', MarketerProductRUViewSet)
marketer_router.register('collection', MarketerCollectionModelViewSet)
marketer_router.register('category', MarketerCategoryModelViewSet)
marketer_router.register('banner', MarketerBannerModelViewSet)
marketer_router.register('story', MarketerStoryViewSet)
marketer_router.register('crm-notification', CRMNotificationView)
marketer_router.register('product-size', ProductSizeView)
marketer_router.register('product-hits', MarketerProductHitsListView)

marketer_urlpatterns = [
    path('marketer/dealer-status/list/', MarketerDealerStatusListView.as_view({'get': 'list'})),
    path('marketer/', include(marketer_router.urls)),
]

# --------------------------- WARE HOUSE MANAGER

warehouse_manager_router = SimpleRouter()
warehouse_manager_router.register('order', WareHouseOrderView, basename='warehouse-order')
warehouse_manager_router.register('product', WareHouseProductViewSet, basename='warehouse-product')
warehouse_manager_router.register('category', WareHouseCategoryViewSet, basename='warehouse-category')
warehouse_manager_router.register('collection', WareHouseCollectionViewSet, basename='warehouse-collection')
warehouse_manager_router.register('inventory', WareHouseInventoryView, basename='warehouse-inventory')
warehouse_manager_router.register('inventory/product/delete', InventoryProductDeleteView,
                                  basename='warehouse-inventory-product-delete')
warehouse_manager_router.register('order-return', ReturnOrderProductView, basename='warehouse-order-return')


warehouse_manager_urlpatterns = [
    path('warehouse-manager/', include(warehouse_manager_router.urls)),
    path('warehouse-manager/report/', WareHouseSaleReportView.as_view()),
    path('warehouse-manager/report/<int:pk>/', WareHouseSaleReportDetailView.as_view()),

]

crm_router = SimpleRouter()
crm_router.register("crm/collection/crud", CollectionCRUDView)
crm_router.register("crm/category/crud", CategoryCRUDView)
crm_router.register("crm/city/crud", CityCRUDView)
crm_router.register("crm/staff/task/list", CRMTaskListView)


crm_router.register("crm/dealer-status/list", DealerStatusListView)

crm_urlpatterns = [

    path("crm/product/images/create/", ProductImagesCreate.as_view()),
    path("crm/city/list/", CityListView.as_view()),
    path("crm/stock/list/", StockListView.as_view()),
    path("crm/category/list/", CategoryListView.as_view()),
    path("crm/price-type/list/", PriceTypeListView.as_view()),
    path("crm/staff/task/response/", TaskResponseView.as_view()),
    path("crm/villages/list/", VillageListView.as_view()),
    path("crm/managers/list/", ManagerShortListView.as_view()),

    path("crm/user/image/cd", UserImageCDView.as_view()),

    path("crm/staff/me-info/", StaffMeInfoView.as_view()),
    path('crm/dealers/filter/', DealersFilterAPIView.as_view()),
    path('crm/products/filter/discount/', FilterProductByDiscountAPIView.as_view()),
    path("", include(crm_router.urls)),
]

# + some_urlpatterns
urlpatterns = (manager_urlpatterns + rop_urlpatterns + director_urlpatterns + crm_urlpatterns + marketer_urlpatterns +
               warehouse_manager_urlpatterns + accountant_urlpatterns + main_director_urlpatterns
               + hr_urlpatterns)
