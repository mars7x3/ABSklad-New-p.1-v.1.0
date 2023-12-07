from django.urls import path, re_path, include
from rest_framework.routers import SimpleRouter

from crm_manager.views import (
    DealerViewSet, WareHouseViewSet, OrderViewSet,
    CategoryListAPIView, CategoryProductListAPIView, ProductRetrieveAPIView,
    BalanceHistoryViewSet, BalancePlusView, ManagerOrderCreateView, WallerViewSet
)

router = SimpleRouter()
router.register("dealers", DealerViewSet)
router.register("warehouses", WareHouseViewSet)
router.register("orders", OrderViewSet)
router.register('balances', WallerViewSet)
router.register('balances/plus', BalanceHistoryViewSet)

urlpatterns = [
    path('categories/', CategoryListAPIView.as_view(), name='crm_manager-categories-list'),
    re_path('^categories/(?P<category_slug>.+)/products/$', CategoryProductListAPIView.as_view(),
            name='crm_manager-category-products-list'),
    re_path('^products/(?P<product_id>.+)/detail$', ProductRetrieveAPIView.as_view(),
            name="crm_manager-products-retrieve"),
    path('balance/plus/', BalancePlusView.as_view(), name="crm_manager-dealer-balance-plus"),
    path('', include(router.urls)),
    path('order/create/', ManagerOrderCreateView.as_view()),  # manager order create
]
