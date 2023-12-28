import datetime

from django.db.models import Case, When
from django.utils import timezone
from rest_framework.filters import SearchFilter
from rest_framework import viewsets, status, mixins, generics
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from crm_general.accountant.permissions import IsAccountant
from crm_general.accountant.serializers import MyOrderListSerializer, MyOrderDetailSerializer, \
    AccountantProductSerializer, AccountantCollectionSerializer, AccountantCategorySerializer, \
    AccountantStockListSerializer, AccountantStockDetailSerializer
from crm_general.views import CRMPaginationClass
from general_service.models import Stock
from order.models import MyOrder
from product.models import AsiaProduct, Collection, Category


class AccountantOrderListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsAccountant]
    queryset = MyOrder.objects.all()
    serializer_class = MyOrderListSerializer
    pagination_class = CRMPaginationClass

    def get_serializer_class(self):
        if self.detail:
            return MyOrderDetailSerializer
        return self.serializer_class

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}

        name = request.query_params.get('name')
        if name:
            kwargs['author__user__name__icontains'] = name

        city = request.query_params.get('city')
        if city:
            kwargs['author__city__slug'] = city

        o_status = request.query_params.get('status')
        if o_status:
            kwargs['status'] = o_status

        type_status = request.query_params.get('type_status')
        if type_status:
            kwargs['type_status'] = type_status

        queryset = queryset.filter(**kwargs)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context()).data

        return self.get_paginated_response(serializer)


class AccountantProductListView(ListModelMixin, GenericViewSet):
    queryset = AsiaProduct.objects.all()
    permission_classes = [IsAuthenticated, IsAccountant]
    serializer_class = AccountantProductSerializer
    pagination_class = CRMPaginationClass

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        pr_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        if pr_status == 'true':
            queryset = queryset.filter(is_active=True)
        elif pr_status == 'false':
            queryset = queryset.filter(is_active=False)

        if search:
            queryset = queryset.filter(title__icontains=search)

        paginator = CRMPaginationClass()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AccountantCollectionListView(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Collection.objects.all()
    permission_classes = [IsAuthenticated, IsAccountant]
    pagination_class = CRMPaginationClass
    serializer_class = AccountantCollectionSerializer

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
        paginator = CRMPaginationClass()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context()).data
        return paginator.get_paginated_response(serializer)


class AccountantCategoryView(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Category.objects.all()
    permission_classes = [IsAuthenticated, IsAccountant]
    pagination_class = CRMPaginationClass
    serializer_class = AccountantCategorySerializer

    def get_serializer_context(self):
        if self.detail:
            return {'request': self.request, 'retrieve': True}
        return {'request': self.request}

    def get_queryset(self):
        collection_slug = self.request.query_params.get('collection_slug')
        if collection_slug:
            return self.queryset.filter(products__collection__slug=collection_slug).distinct()
        else:
            return self.queryset


class AccountantStockViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Stock.objects.all()
    permission_classes = [IsAuthenticated, IsAccountant]
    pagination_class = CRMPaginationClass
    serializer_class = AccountantStockListSerializer
    retrieve_serializer_class = AccountantStockDetailSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        stock_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        if stock_status == 'true':
            queryset = queryset.filter(is_active=True)
        elif stock_status == 'false':
            queryset = queryset.filter(is_active=False)

        if search:
            queryset = queryset.filter(city__icontains=search)
        paginator = CRMPaginationClass()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context()).data
        return paginator.get_paginated_response(serializer)

    def get_serializer_class(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class
