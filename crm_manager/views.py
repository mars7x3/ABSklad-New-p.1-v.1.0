from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, generics, mixins, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from account.models import DealerProfile, StaffProfile
from crm_manager.filters import OrderFilter
from crm_manager.paginations import ProfilePagination, OrderPagination, CategoryPagination, ProductPagination
from crm_manager.permissions import IsManager
from crm_manager.serializers import DealerProfileSerializer, StaffProfileSerializer, OrderListSerializer, \
    OrderReceiptSerializer
from order.models import MyOrder, OrderReceipt
from product.models import Category, AsiaProduct
from product.serializers import CategoryListSerializer, ProductListSerializer


class DealerViewSet(
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    queryset = DealerProfile.objects.select_related("user", "city").all()
    serializer_class = DealerProfileSerializer
    pagination_class = ProfilePagination
    permission_classes = (IsAuthenticated, IsManager,)
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
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    queryset = StaffProfile.objects.select_related("user", "city").filter(user__status="warehouse")
    serializer_class = StaffProfileSerializer
    pagination_class = ProfilePagination
    permission_classes = (IsAuthenticated, IsManager)
    filter_backends = (OrderingFilter,)
    ordering_fields = ("user__date_joined",)

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


class OrderListAPIView(mixins.ListModelMixin, generics.GenericAPIView):
    queryset = MyOrder.objects.filter(is_active=True)
    serializer_class = OrderListSerializer
    pagination_class = OrderPagination
    permission_classes = (IsAuthenticated, IsManager)
    filter_backends = (SearchFilter, OrderFilter, OrderingFilter)
    search_fields = ("name",)
    ordering_fields = ("price", "created_at", "paid_at", "released_at")
    lookup_field = "id"
    lookup_url_kwarg = "order_id"

    def get_queryset(self):
        return super().get_queryset().filter(author__city=self.request.user.staff_profile.city)

    @extend_schema(responses={status.HTTP_200_OK: OrderReceiptSerializer(many=True)})
    @action(methods=['GET'], detail=True, url_path="receipts")
    def get_order_receipts(self, request, order_id):
        receipts = OrderReceipt.objects.filter(order_id=order_id, order__is_active=True)
        return Response(OrderReceiptSerializer(instance=receipts, many=True).data)

    # TODO: ордер со статусом новый или (оплачено, оплата = баллы) -> is_active = False and update


class CategoryViewSet(mixins.ListModelMixin, generics.GenericAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategoryListSerializer
    pagination_class = CategoryPagination
    permission_classes = (IsAuthenticated, IsManager)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("title",)
    ordering_fields = ("title",)


class ProductViewSet(mixins.ListModelMixin, generics.GenericAPIView):
    queryset = AsiaProduct.objects.filter(is_active=True)
    serializer_class = ProductListSerializer
    pagination_class = ProductPagination
    permission_classes = (IsAuthenticated, IsManager)



# катеории и товары (кол. и цена по городу )
# баланс

"""
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzA0MjMxNjA3LCJpYXQiOjE3MDE2Mzk2MDcsImp0aSI6ImM3MmFkMThiYTY5ZjQ2OTdhMzZkZTkwN2IzNzZhYmEzIiwidXNlcl9pZCI6Mn0.nZDSlmVWH224i9k-IYVoBRI5ePOVR7UVeCXSz77BHOg
"""