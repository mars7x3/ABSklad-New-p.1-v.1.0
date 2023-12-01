from django.db.models import Q
from rest_framework import viewsets, mixins, status, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from product.models import Category, AsiaProduct, Review, Collection, FilterMaxMin
from product.permissions import IsAuthor
from product.serializers import CategoryListSerializer, ProductListSerializer, ReviewSerializer, \
    ProductDetailSerializer, CollectionListSerializer


class ReviewCDView(mixins.CreateModelMixin, mixins.DestroyModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsAuthor]
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer


class CategoryListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Category.objects.filter(is_active=True, is_show=True)
    serializer_class = CategoryListSerializer


class CollectionListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Collection.objects.all()
    serializer_class = CollectionListSerializer


class ProductListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = AsiaProduct.objects.filter(is_active=True, is_show=True)
    serializer_class = ProductListSerializer

    def get_serializer_class(self):
        if self.kwargs.get('pk'):
            return ProductDetailSerializer
        else:
            return ProductListSerializer

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}
        dealer = request.user.dealer_profile

        discount = request.query_params.get('discount')
        if discount:
            kwargs['prices__discount__gt'] = 0

        category = request.query_params.get('category')
        if category:
            kwargs['category__slug'] = category

        collection = request.query_params.get('collection')
        if collection:
            kwargs['collection__slug'] = collection

        price = request.query_params.get('price')
        if price:
            start_price = price.split('$')[0]
            end_price = price.split('$')[1]
            kwargs['prices__price__gte'] = start_price
            kwargs['prices__d_status'] = dealer.dealer_status
            kwargs['prices__city'] = dealer.price_city
            kwargs['prices__price__lte'] = end_price

        text = request.query_params.get('text')
        if text:
            queryset = queryset.filter(
                Q(title__icontains=text) | Q(description__icontains=text)
            )

        products = queryset.filter(**kwargs)
        response_data = self.get_serializer(products, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class ReviewListView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get('product_id')
        product = AsiaProduct.objects.filter(id=product_id).first()
        if product:
            response_data = ReviewSerializer(product.reviews.filter(is_active=True), many=True,
                                             context=self.get_renderer_context()).data
            return Response(response_data, status=status.HTTP_200_OK)
        return Response({'text': "Продукт не существует!"}, status=status.HTTP_400_BAD_REQUEST)


class FilterMaxMinView(APIView):
    def get(self, request):
        max_min = FilterMaxMin.objects.first()
        return Response({'max': max_min.max_price, 'min': max_min.min_price}, status=status.HTTP_200_OK)

