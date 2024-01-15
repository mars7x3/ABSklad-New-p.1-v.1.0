from django.urls import path

from .views import StockGroupAPIView, StockGroupByWeekAPIView

urlpatterns = [
    path("stocks/", StockGroupAPIView.as_view()),
    path("stocks-by-weeks/", StockGroupByWeekAPIView.as_view())
]
