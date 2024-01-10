from collections import OrderedDict

from django.db.models import Q
from rest_framework.response import Response
from rest_framework import viewsets, status, generics, mixins
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from account.models import MyUser, DealerStatus, DealerProfile
from crm_general.permissions import IsStaff
from crm_general.serializers import StaffListSerializer, CollectionCRUDSerializer, CityListSerializer, \
    StockListSerializer, DealerStatusListSerializer, CategoryListSerializer, CategoryCRUDSerializer, \
    CRMTaskResponseSerializer, CityCRUDSerializer, PriceTypeListSerializer, DealerProfileSerializer, \
    ShortProductSerializer
from general_service.models import City, Stock, PriceType
from order.db_request import query_debugger
from product.models import Collection, AsiaProduct, ProductImage, Category
from promotion.models import Discount


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


class CategoryCRUDView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsStaff]
    queryset = Category.objects.all()
    serializer_class = CategoryCRUDSerializer

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


class DealerStatusListView(mixins.ListModelMixin,
                           GenericViewSet):
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


class CRMTaskUpdateAPIView(generics.UpdateAPIView):
    permission_classes = (IsAuthenticated, IsStaff)
    serializer_class = CRMTaskResponseSerializer
    lookup_field = "id"
    lookup_url_kwarg = "response_task_id"

    def get_queryset(self):
        return (
            self.request.user.task_responses
            .select_related("task")
            .prefetch_related("response_files")
            .only("id", "task", "grade", "is_done")
            .all()
        )


class CityCRUDView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsStaff]
    queryset = City.objects.all()
    serializer_class = CityCRUDSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = not instance.is_active
        instance.save()
        return Response({'text': 'Success!'}, status=status.HTTP_200_OK)


class StaffMeInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        response_data = {
            "id": user.id,
            "status": user.status,
            "name": user.name,
            "email": user.email,
            "image": request.build_absolute_uri(user.image.url) if user.image else None,
            "phone": user.phone
        }
        return Response(response_data, status=status.HTTP_200_OK)


class PriceTypeListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsStaff]
    queryset = PriceType.objects.filter(is_active=True)
    serializer_class = PriceTypeListSerializer


class DealersFilterAPIView(APIView):
    @query_debugger
    def post(self, request):
        cities = self.request.data.get('cities', [])
        categories = self.request.data.get('categories', [])
        if not cities and not categories:
            return Response({'detail': 'filter by cities or categories needed'}, status=status.HTTP_400_BAD_REQUEST)

        base_query = Q(user__is_active=True)

        if cities:
            base_query &= Q(city__in=cities)

        if categories:
            base_query &= Q(dealer_status__in=categories)

        dealers = DealerProfile.objects.filter(base_query)

        serializer = DealerProfileSerializer(dealers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FilterProductByDiscountAPIView(APIView):
    def get(self, request, *args, **kwargs):
        category = self.request.query_params.get('category')
        products = AsiaProduct.objects.filter(is_active=True, is_discount=False, category=category)
        discounts = Discount.objects.all()
        for discount in discounts:
            products = products.exclude(id__in=discount.products.values_list('id', flat=True))

        serializer = ShortProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
