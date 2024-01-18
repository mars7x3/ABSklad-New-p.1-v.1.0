from django.urls import path, re_path

from .views import (
    StockGroupAPIView, StockGroupByWeekAPIView,
    DealerFundsView, DealerView, DealerSalesView, DealerProductView, ProductSalesView, ProductDealersView, ProductView,
    TransactionView, OrderView
)

urlpatterns = [
    path("stocks/", StockGroupAPIView.as_view()),
    path("stocks-by-weeks/", StockGroupByWeekAPIView.as_view()),

    re_path("^dealer-funds/(?P<date>.+)/$", DealerFundsView.as_view()),
    re_path("^dealer-sales/(?P<stock_id>.+)/(?P<date>.+)/$", DealerSalesView.as_view()),
    re_path("^dealer-products/(?P<stock_id>.+)/(?P<date>.+)/$", DealerProductView.as_view()),
    re_path("^dealers/(?P<user_id>.+)/(?P<stock_id>.+)/(?P<date>.+)/$", DealerView.as_view()),

    re_path("^product-sales/(?P<stock_id>.+)/(?P<date>.+)/$", ProductSalesView.as_view()),
    re_path("^product-dealers/(?P<stock_id>.+)/(?P<date>.+)/$", ProductDealersView.as_view()),
    re_path("^products/(?P<product_id>.+)/(?P<stock_id>.+)/(?P<date>.+)/$", ProductView.as_view()),

    re_path("^transactions/(?P<date>.+)/$", TransactionView.as_view()),
    re_path("^orders/(?P<date>.+)/$", OrderView.as_view()),

]
