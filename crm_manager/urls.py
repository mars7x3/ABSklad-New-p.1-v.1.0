from django.urls import path, re_path, include
from rest_framework.routers import SimpleRouter

from crm_manager.views import (
    DealerViewSet, WareHouseViewSet, OrderViewSet,
    CategoryListAPIView, CategoryProductListAPIView, ProductRetrieveAPIView,
    CRMBalanceHistoryListView, ManagerOrderListView, ManagerOrderCreateView, ManagerOrderDeactivateView,
    ManagerBalancePlusView
)

router = SimpleRouter()
router.register("dealers", DealerViewSet)
router.register("warehouses", WareHouseViewSet)
router.register('balance/plus/list', CRMBalanceHistoryListView)
router.register('order/list', ManagerOrderListView)

urlpatterns = [
    path('category-inventories/', CategoryListAPIView.as_view(), name='crm_manager-categories-list'),
    re_path('^categories/(?P<category_slug>.+)/product-inventories$', CategoryProductListAPIView.as_view(),
            name='crm_manager-category-products-list'),
    re_path('^products/(?P<product_id>.+)/detail$', ProductRetrieveAPIView.as_view(),
            name="crm_manager-products-retrieve"),
    path('order/create/', ManagerOrderCreateView.as_view()),  # manager order create
    path('order/deactivate/', ManagerOrderDeactivateView.as_view()),  # manager order deactivate

    path('balance/plus/create/', ManagerBalancePlusView.as_view()),
    path('', include(router.urls)),
]
