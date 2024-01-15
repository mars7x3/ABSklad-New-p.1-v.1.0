from django.urls import path

from .views import StockGroupAPIView


urlpatterns = [
    path("stocks/", StockGroupAPIView.as_view()),
]
