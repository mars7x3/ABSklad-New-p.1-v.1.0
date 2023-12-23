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

from .marketer.views import (
    MarketerProductRUViewSet, MarketerCollectionModelViewSet, MarketerCategoryModelViewSet, ProductSizeDestroyView,
    MarketerBannerModelViewSet, MarketerStoryViewSet, CRMNotificationView, MarketerDealerStatusListView
)
from .warehouse_manager.views import (
    WareHouseOrderView, WareHouseCollectionViewSet, WareHouseProductViewSet, WareHouseCategoryViewSet
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
director_router.register("director/dealer/list", DirectorStaffListView)


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
crm_router.register("crm/dealer-status/list", DealerStatusListView)

crm_urlpatterns = [
    path('crm/product/images/create/', ProductImagesCreate.as_view()),
    path("crm/city/list/", CityListView.as_view()),
    path("crm/stock/list/", StockListView.as_view()),
    path("crm/category/list/", CategoryListView.as_view()),


    path("crm/user/image/cd", UserImageCDView.as_view()),


    path('', include(crm_router.urls)),
]


marketer_router = SimpleRouter()
marketer_router.register('product', MarketerProductRUViewSet)
marketer_router.register('collection', MarketerCollectionModelViewSet)
marketer_router.register('category', MarketerCategoryModelViewSet)
marketer_router.register('banner', MarketerBannerModelViewSet)
marketer_router.register('story', MarketerStoryViewSet)
marketer_router.register('crm-notification', CRMNotificationView)


marketer_urlpatterns = [
    path('marketer/product-sizes/<int:pk>/', ProductSizeDestroyView.as_view({'delete': 'destroy'})),
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
]

# + some_urlpatterns
urlpatterns = (manager_urlpatterns + rop_urlpatterns + director_urlpatterns + crm_urlpatterns + marketer_urlpatterns +
               warehouse_manager_urlpatterns)


