from django.urls import path, re_path

from .views import (
    StockGroupAPIView, StockGroupByWeekAPIView,
    DealerFundsView, DealerView, DealerSalesView, DealerProductView, ProductSalesView, ProductDealersView, ProductView,
    TransactionView, OrderView, TransactionUserView, OrderDetailsView
)

urlpatterns = [
    path("stocks/", StockGroupAPIView.as_view()),
    path("stocks-by-weeks/", StockGroupByWeekAPIView.as_view()),

    re_path("^dealer-funds/(?P<date>.+)/$", DealerFundsView.as_view()),
    re_path("^dealer-sales/(?P<date>.+)/$", DealerSalesView.as_view()),
    re_path("^dealer-products/(?P<date>.+)/$", DealerProductView.as_view()),
    re_path("^dealers/(?P<user_id>.+)/(?P<date>.+)/$", DealerView.as_view()),

    re_path("^product-sales/(?P<date>.+)/$", ProductSalesView.as_view()),
    re_path("^product-dealers/(?P<date>.+)/$", ProductDealersView.as_view()),
    re_path("^products/(?P<product_id>.+)/(?P<date>.+)/$", ProductView.as_view()),

    re_path("^grouped-transactions/(?P<date>.+)/$", TransactionUserView.as_view()),
    re_path("^transactions/(?P<date>.+)/$", TransactionView.as_view()),
    re_path("^orders/(?P<date>.+)/$", OrderView.as_view()),
    re_path("^order-details/(?P<date>.+)/$", OrderDetailsView.as_view()),
]
