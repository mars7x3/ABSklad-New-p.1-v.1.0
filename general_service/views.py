from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Stock, City
from .serializers import StockSerializer, CitySerializer


class CategoryListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Stock.objects.filter(is_active=True, is_show=True)
    serializer_class = StockSerializer


class CityListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = City.objects.filter(is_active=True, is_show=True)
    serializer_class = CitySerializer