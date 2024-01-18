from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

router.register('dealer/order/list', MyOrderListView)  # dealer order list

urlpatterns = [
    path('dealer/order/create/', MyOrderCreateView.as_view()),  # dealer order create
    path('dealer/order/receipt/add/', OrderReceiptAddView.as_view()),  # dealer order receipt add

    path('dealer/purchase/analysis/', PurchaseAnalysisView.as_view()),

    path('dealer/cart/add/', CartAddView.as_view()),  # cart add
    path('dealer/cart/list/', CartListView.as_view()),  # cart list

    path('', include(router.urls)),
]
