from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated

from order.models import MyOrder
from product.models import AsiaProduct, Collection, Category
from .permissions import IsWareHouseManager
from crm_general.paginations import GeneralPurposePagination, ProductPagination
from .serializers import OrderListSerializer, OrderDetailSerializer, WareHouseProductListSerializer, \
    WareHouseCollectionListSerializer, WareHouseCategoryListSerializer, WareHouseCategoryDetailSerializer
from .mixins import WareHouseManagerMixin


class WareHouseOrderView(WareHouseManagerMixin, ReadOnlyModelViewSet):
    queryset = MyOrder.objects.all()
    permission_classes = [IsAuthenticated, IsWareHouseManager]
    pagination_class = GeneralPurposePagination
    serializer_class = OrderListSerializer
    retrieve_serializer_class = OrderDetailSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        order_status = self.request.query_params.get('status')
        type_status = self.request.query_params.get('type_status')
        search = self.request.query_params.get('search')
        if status:
            queryset = queryset.filter(status=order_status)
        if type_status:
            queryset = queryset.filter(type_status=type_status)

        if search:
            queryset = queryset.filter(Q(name__iconatins=search), Q(gmail__icontains=search))

        paginator = GeneralPurposePagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context())
        return paginator.get_paginated_response(serializer.data)

    def get_serializer_class(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class

    def get_queryset(self):
        return self.queryset.filter(stock=self.warehouse_profile.stock)

    @action(methods=['PATCH'], detail=False, url_path='update-status')
    def update_order_status(self, request):
        order_status = self.request.data.get('status')
        order_id = self.request.data.get('order_id')
        if order_id:
            order = MyOrder.objects.get(id=order_id)
        else:
            return Response({'detail': 'order_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if order_status == 'sent':
            if order.status == 'paid':
                order.status = 'sent'
                order.save()
                return Response({'detail': 'Order status successfully changed to "sent"'},
                                status=status.HTTP_200_OK)
            return Response({'detail': 'Order status must be "paid" to change to "sent"'},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Incorrect order status'}, status=status.HTTP_400_BAD_REQUEST)


class WareHouseProductViewSet(ListModelMixin, RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = AsiaProduct.objects.all()
    serializer_class = WareHouseProductListSerializer
    permission_classes = [IsAuthenticated, IsWareHouseManager]
    pagination_class = ProductPagination

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        product_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        if product_status == 'active':
            queryset = queryset.filter(is_active=True)
        elif product_status == 'inactive':
            queryset = queryset.filter(is_active=False)

        if search:
            queryset = queryset.filter(title__icontains=search)

        paginator = ProductPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context()).data
        return paginator.get_paginated_response(serializer)

    def get_queryset(self):
        return self.queryset.filter(counts__stock=self.request.user.warehouse_profile.stock)


class WareHouseCollectionViewSet(ListModelMixin,
                                 RetrieveModelMixin,
                                 GenericViewSet):
    queryset = Collection.objects.all()
    permission_classes = [IsAuthenticated, IsWareHouseManager]
    pagination_class = ProductPagination
    serializer_class = WareHouseCollectionListSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        c_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')

        if c_status == 'active':
            queryset = queryset.filter(is_active=True)
        elif c_status == 'inactive':
            queryset = queryset.filter(is_active=False)

        if search:
            queryset = queryset.filter(title__icontains=search)
        paginator = GeneralPurposePagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context()).data
        return paginator.get_paginated_response(serializer)


class WareHouseCategoryViewSet(ListModelMixin,
                               RetrieveModelMixin,
                               GenericViewSet):
    queryset = Category.objects.all()
    permission_classes = [IsAuthenticated, IsWareHouseManager]
    pagination_class = ProductPagination
    serializer_class = WareHouseCategoryListSerializer
    retrieve_serializer_class = WareHouseCategoryDetailSerializer

    def get_serializer_context(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class

