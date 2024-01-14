from django.urls import path

from .views import StockGroupedStatsAPIView


urlpatterns = [
    path("stocks/", StockGroupedStatsAPIView.as_view()),
]
