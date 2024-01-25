from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from crm_general.serializers import StockListSerializer
from .models import Stock, City, Requisite, RequisiteCategory, PriceType
from .serializers import StockSerializer, CitySerializer, RequisiteListSerializer, RequisiteCategorySerializer


class CategoryListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Stock.objects.filter(is_active=True, is_show=True)
    serializer_class = StockSerializer


class StockListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Stock.objects.filter(is_active=True, is_show=True)
    serializer_class = StockListSerializer


class CityListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = City.objects.filter(is_active=True, is_show=True)
    serializer_class = CitySerializer


class RequisiteListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        category = request.query_params.get('category')
        city = request.user.dealer_profile.village.city

        requisite = Requisite.objects.filter(requisite_cities__city=city, category_id=category, is_active=True).first()
        response = RequisiteListSerializer(requisite, context=self.get_renderer_context()).data
        return Response(response, status=status.HTTP_200_OK)


class RequisiteCategoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        requisite = RequisiteCategory.objects.filter(is_active=True)
        response = RequisiteCategorySerializer(requisite, many=True, context=self.get_renderer_context()).data
        return Response(response, status=status.HTTP_200_OK)




