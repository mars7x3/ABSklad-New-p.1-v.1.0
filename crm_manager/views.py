import datetime

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, generics, mixins, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.models import DealerProfile, StaffProfile, BalancePlus, MyUser, BalancePlusFile
from crm_manager.mixins import ManagerMixin
from order.models import MyOrder, OrderReceipt, OrderProduct
from product.models import Category, AsiaProduct

from crm_manager.filters import OrderFilter
from crm_manager.paginations import ProfilePagination, OrderPagination, AppPaginationClass
from crm_manager.permissions import OrderPermission
from crm_manager.serializers import (
    DealerProfileSerializer, StaffProfileSerializer, OrderSerializer,
    OrderReceiptSerializer, OrderProductSerializer, CategoryInventorySerializer,
    MangerOrderCreateSerializer, ManagerOrderDetailSerializer, ManagerOrderListSerializer, CRMBalancePlusSerializer,
    ShortProductSerializer, ProductSerializer
)


class DealerViewSet(
    ManagerMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    queryset = DealerProfile.objects.select_related("user", "city").all()
    serializer_class = DealerProfileSerializer
    pagination_class = ProfilePagination
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("name",)
    ordering_fields = ("name", "user__date_joined")
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'

    def get_queryset(self):
        return super().get_queryset().filter(city=self.request.user.staff_profile.city)

    @extend_schema(responses={status.HTTP_200_OK: None, status.HTTP_404_NOT_FOUND: None}, request=None)
    @action(methods=['PATCH'], detail=True, url_path='change-activity')
    def change_user_activity(self, request, user_id):
        dealer_profile = self.get_object()
        user = dealer_profile.user
        user.is_active = not user.is_active
        user.save()
        return Response(status=status.HTTP_200_OK)


class WareHouseViewSet(
    ManagerMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    queryset = StaffProfile.objects.select_related("user", "city").filter(user__status="warehouse")
    serializer_class = StaffProfileSerializer
    pagination_class = ProfilePagination
    filter_backends = (OrderingFilter,)
    ordering_fields = ("user__date_joined",)
    lookup_field = "user_id"
    lookup_url_kwarg = "user_id"

    def get_queryset(self):
        return super().get_queryset().filter(stock=self.request.user.staff_profile.stock)

    @extend_schema(responses={status.HTTP_200_OK: None, status.HTTP_404_NOT_FOUND: None}, request=None)
    @action(methods=['PATCH'], detail=True, url_path='change-activity')
    def change_user_activity(self, request, user_id):
        warehouse_profile = self.get_object()
        user = warehouse_profile.user
        user.is_active = not user.is_active
        user.save()
        return Response(status=status.HTTP_200_OK)


class OrderViewSet(ManagerMixin, mixins.ListModelMixin, generics.GenericAPIView):
    queryset = MyOrder.objects.all()
    serializer_class = OrderSerializer
    pagination_class = OrderPagination
    filter_backends = (SearchFilter, OrderFilter, OrderingFilter)
    search_fields = ("name",)
    ordering_fields = ("price", "created_at", "paid_at", "released_at")
    lookup_field = "id"
    lookup_url_kwarg = "order_id"

    def get_permissions(self):
        return [*super().get_permissions(), OrderPermission()]

    def get_queryset(self):
        return super().get_queryset().filter(author__city=self.request.user.staff_profile.city)

    @extend_schema(responses={status.HTTP_200_OK: OrderReceiptSerializer(many=True)})
    @action(methods=['GET'], detail=True, url_path="receipts")
    def get_order_receipts(self, request, order_id):
        receipts = OrderReceipt.objects.filter(order_id=order_id)
        return Response(OrderReceiptSerializer(instance=receipts, many=True).data)

    @extend_schema(responses={status.HTTP_200_OK: OrderProductSerializer(many=True)})
    @action(methods=['GET'], detail=True, url_path="products")
    def get_order_products(self, request, order_id):
        products = OrderProduct.objects.filter(order_id=order_id)
        return Response(OrderProductSerializer(instance=products).data)

    @extend_schema(responses={status.HTTP_200_OK: None, status.HTTP_404_NOT_FOUND: None}, request=None)
    @action(methods=['PATCH'], detail=True, url_path='change-activity')
    def change_user_activity(self, request, order_id):
        order = self.get_object()
        order.is_active = not order.is_active
        order.save()
        return Response(status=status.HTTP_200_OK)


class CategoryListAPIView(ManagerMixin, generics.ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategoryInventorySerializer
    filter_backends = (SearchFilter,)
    search_fields = ("title", "slug")


class CategoryProductListAPIView(ManagerMixin, generics.ListAPIView):
    queryset = AsiaProduct.objects.filter(is_active=True)
    serializer_class = ShortProductSerializer
    lookup_field = 'category__slug'
    lookup_url_kwarg = 'category_slug'

    def get_queryset(self):
        return super().get_queryset().filter(**{self.lookup_field: self.kwargs[self.lookup_url_kwarg]})


class ProductRetrieveAPIView(ManagerMixin, generics.RetrieveAPIView):
    queryset = AsiaProduct.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'product_id'


class ManagerOrderCreateView(ManagerMixin, generics.CreateAPIView):
    queryset = MyOrder.objects.all()
    serializer_class = MangerOrderCreateSerializer


class ManagerOrderDeactivateView(ManagerMixin, APIView):
    def post(self, request):
        order_id = request.data.get('order_id')
        order = MyOrder.objects.filter(id=order_id).first()
        response_data = MangerOrderCreateSerializer(order, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class ManagerOrderListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = MyOrder.objects.all()
    serializer_class = ManagerOrderDetailSerializer
    pagination_class = AppPaginationClass

    def get_queryset(self):
        queryset = self.queryset.filter(author__city=self.request.user.staff_profile.city)
        return queryset

    def get_serializer_class(self):
        if self.kwargs.get('pk'):
            return ManagerOrderDetailSerializer
        else:
            return ManagerOrderListSerializer

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}
        city = request.query_params.get('city')
        o_status = request.query_params.get('status')

        if city:
            kwargs['stock__city__slug'] = city

        if o_status:
            kwargs['status'] = o_status

        queryset = queryset.filter(**kwargs)

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context()).data

        return self.get_paginated_response(serializer)


class ManagerBalancePlusView(ManagerMixin, APIView):
    def post(self, request):
        amount = request.data.get('amount')
        files = request.FILES.getlist('files')
        user_id = request.data.get('user_id')
        user = MyUser.objects.filter(id=user_id).first()
        dealer = user.dealer_profile
        if amount and files:
            # TODO: добавить синхронизацию с 1С
            balance = BalancePlus.objects.create(dealer=dealer, amount=amount)
            BalancePlusFile.objects.bulk_create([BalancePlusFile(balance=balance, file=i) for i in files])
            return Response({'text': 'Завявка принята!'}, status=status.HTTP_200_OK)
        return Response({'text': 'amount and files is required!'}, status=status.HTTP_400_BAD_REQUEST)


class CRMBalanceHistoryListView(ManagerMixin, viewsets.ReadOnlyModelViewSet):
    queryset = BalancePlus.objects.all()
    serializer_class = CRMBalancePlusSerializer
    pagination_class = AppPaginationClass

    def get_queryset(self):
        queryset = self.queryset.filter(dealer__city=self.request.user.staff_profile.city)
        return queryset

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}
        price = request.query_params.get('start')
        end = request.query_params.get('end')
        is_success = request.query_params.get('is_success')

        if price and end:
            start_date = timezone.make_aware(datetime.datetime.strptime(price, "%d-%m-%Y"))
            end_date = timezone.make_aware(datetime.datetime.strptime(end, "%d-%m-%Y"))
            kwargs['created_at__gte'] = start_date
            kwargs['created_at__lte'] = end_date

        if is_success:
            kwargs['is_success'] = bool(int(is_success))

        queryset = queryset.filter(**kwargs)
        page = self.paginate_queryset(queryset)
        response_data = self.get_serializer(page, many=True, context=self.get_renderer_context()).data
        return self.get_paginated_response(response_data)
