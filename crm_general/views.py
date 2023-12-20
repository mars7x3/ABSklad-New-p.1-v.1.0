from collections import OrderedDict

from rest_framework.response import Response
from rest_framework import viewsets, status, generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from account.models import MyUser, DealerStatus
from crm_general.permissions import IsStaff
from crm_general.serializers import StaffListSerializer, CollectionCRUDSerializer, CityListSerializer, \
    StockListSerializer, DealerStatusListSerializer, CategoryListSerializer
from general_service.models import City, Stock
from product.models import Collection, AsiaProduct, ProductImage, Category


class CRMPaginationClass(PageNumberPagination):
    page_size = 1
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('total_pages', self.page.paginator.num_pages),
            ('page', self.page.number),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data),
            ('results_count', len(data)),
            ('total_results', self.page.paginator.count),
        ]))


class StaffListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsStaff]
    queryset = MyUser.objects.exclude(status__in=['dealer', 'dealer_1c'])
    serializer_class = StaffListSerializer


class CollectionCRUDView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsStaff]
    queryset = Collection.objects.all()
    serializer_class = CollectionCRUDSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = not instance.is_active
        instance.save()
        return Response({'text': 'Success!'}, status=status.HTTP_200_OK)


class CityListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsStaff]
    queryset = City.objects.filter(is_active=True)
    serializer_class = CityListSerializer


class StockListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsStaff]
    queryset = Stock.objects.filter(is_active=True)
    serializer_class = StockListSerializer


class DealerStatusListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsStaff]
    queryset = DealerStatus.objects.all()
    serializer_class = DealerStatusListSerializer


class CategoryListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsStaff]
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategoryListSerializer


class ProductImagesCreate(APIView):
    """
    {"product_id": "product_id", "images": [file, file], "delete_ids": [image_id, image_id]}
    """
    permission_classes = [IsAuthenticated, IsStaff]

    def post(self, request):
        product_id = request.data.get('product_id')
        images = request.FILES.getlist('images')
        delete_ids = request.data.get('delete_ids')
        product = AsiaProduct.objects.filter(id=product_id).first()
        if product:
            delete_images = product.images.filter(id__in=delete_ids)
            if delete_images:
                delete_images.delete()
            if images:
                ProductImage.objects.bulk_create([ProductImage(product=product, image=i) for i in images])
            return Response({'text': 'Success!'}, status=status.HTTP_200_OK)
        return Response({'text': 'Продукт отсутствует!'}, status=status.HTTP_400_BAD_REQUEST)


class UserImageCDView(APIView):
    """
    {"user_id": user_id, "is_delete": bool(true/false), "image": file}
    """
    permission_classes = [IsAuthenticated, IsStaff]

    def post(self, request):
        user_id = request.data.get('user_id')
        image = request.FILES.get('image')
        is_delete = request.data.get('is_delete')
        user = MyUser.objects.filter(id=user_id).first()
        if is_delete:
            user.image.delete()
            return Response({"text": "Success!"}, status=status.HTTP_200_OK)
        user.image = image
        user.save()
        image_url = request.build_absolute_uri(user.image.url)
        return Response({"url": image_url}, status=status.HTTP_200_OK)
