from django.db.models import Sum, DecimalField, Q, Value
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, generics, mixins, parsers
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response

from account.models import DealerProfile, StaffProfile, BalancePlus, Wallet
from crm_manager.mixins import ManagerMixin
from order.db_request import query_debugger
from order.models import MyOrder
from product.models import Category, AsiaProduct

from crm_general.serializers import ActivitySerializer
from crm_general.paginations import ProfilePagination
from crm_manager.filters import OrderFilter, BalancePlusFilter, WallerFilter
from crm_manager.paginations import AppPaginationClass
from crm_manager.permissions import OrderPermission
from crm_manager.serializers import (
    CRMDealerProfileSerializer, CRMWareHouseProfileSerializer, CRMCategorySerializer,
    ManagerOrderSerializer, ManagerShortOrderSerializer,
    CRMProductSerializer, CRMShortProductSerializer,
    CRMBalancePlusSerializer, CRMBalancePlusCreateSerializer, CRMWalletSerializer, CRMWalletAmountSerializer
)


class DealerViewSet(
    ManagerMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    queryset = DealerProfile.objects.select_related("user", "city", "price_city").all()
    serializer_class = CRMDealerProfileSerializer
    pagination_class = ProfilePagination
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("name",)
    ordering_fields = ("name", "user__date_joined")
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'

    def get_queryset(self):
        return super().get_queryset().filter(city=self.request.user.staff_profile.city)

    @query_debugger
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(responses={"200": ActivitySerializer, "404": None}, request=None)
    @action(methods=['PATCH'], detail=True, url_path='change-activity', filter_backends=[])
    def change_user_activity(self, request, user_id):
        dealer_profile = self.get_object()
        user = dealer_profile.user
        user.is_active = not user.is_active
        user.save()
        return Response(ActivitySerializer(data={"active": user.is_active}, many=False).data)


class WareHouseViewSet(
    ManagerMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    queryset = StaffProfile.objects.select_related("user", "city").filter(user__status="warehouse")
    serializer_class = CRMWareHouseProfileSerializer
    pagination_class = ProfilePagination
    filter_backends = (OrderingFilter,)
    ordering_fields = ("user__date_joined",)
    lookup_field = "user_id"
    lookup_url_kwarg = "user_id"

    def get_queryset(self):
        return super().get_queryset().filter(stock=self.request.user.staff_profile.stock)

    @extend_schema(responses={"200": ActivitySerializer, "404": None}, request=None)
    @action(methods=['PATCH'], detail=True, url_path='change-activity', filter_backends=[])
    def change_user_activity(self, request, user_id):
        warehouse_profile = self.get_object()
        user = warehouse_profile.user
        user.is_active = not user.is_active
        user.save()
        return Response(ActivitySerializer(data={"active": user.is_active}, many=False).data)


# Заказы:
# sum тотал прайс
# sum приход денег
# sum отгруженных заказов

class OrderViewSet(ManagerMixin, viewsets.ReadOnlyModelViewSet):
    queryset = MyOrder.objects.select_related("stock").all()
    serializer_class = ManagerShortOrderSerializer
    retrieve_serializer_class = ManagerOrderSerializer
    pagination_class = AppPaginationClass
    filter_backends = (SearchFilter, OrderFilter, OrderingFilter)
    search_fields = ("name",)
    ordering_fields = ("id", "price", "created_at", "paid_at", "released_at")
    lookup_field = "id"
    lookup_url_kwarg = "order_id"

    def get_permissions(self):
        return [*super().get_permissions(), OrderPermission()]

    def get_queryset(self):
        queryset = super().get_queryset().filter(author__city=self.request.user.staff_profile.city)
        if self.detail:
            return queryset.prefetch_related("receipts", "products")
        return queryset.only("id", "name", "price", "status", "created_at", "paid_at", "released_at", "stock")

    def get_serializer_class(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class

    @extend_schema(responses={"200": ActivitySerializer, "404": None}, request=None)
    @action(methods=['PATCH'], detail=True, url_path='deactivate', filter_backends=[])
    def change_user_activity(self, request, order_id):
        order = self.get_object()
        order.is_active = False
        order.save()
        return Response(ActivitySerializer(data={"active": False}).data)


class CategoryListAPIView(ManagerMixin, generics.ListAPIView):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CRMCategorySerializer
    filter_backends = (SearchFilter,)
    search_fields = ("title", "slug")


class CategoryProductListAPIView(ManagerMixin, generics.ListAPIView):
    queryset = AsiaProduct.objects.filter(is_active=True)
    serializer_class = CRMShortProductSerializer
    lookup_field = 'category__slug'
    lookup_url_kwarg = 'category_slug'

    def get_queryset(self):
        return super().get_queryset().filter(**{self.lookup_field: self.kwargs[self.lookup_url_kwarg]})


class ProductRetrieveAPIView(ManagerMixin, generics.RetrieveAPIView):
    queryset = AsiaProduct.objects.filter(is_active=True)
    serializer_class = CRMProductSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'product_id'


class ManagerOrderCreateView(ManagerMixin, generics.CreateAPIView):
    """
    Создание заказа

    В поле products_count необходимо отправлять объект где ключи это идентификатор продукта, а значением будет количесво
    """
    serializer_class = ManagerOrderSerializer


class WallerViewSet(ManagerMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = CRMWalletSerializer
    pagination_class = AppPaginationClass
    filter_backends = (WallerFilter,)

    @extend_schema(
        responses={"200": CRMWalletAmountSerializer(many=False)},
        filters=True,
    )
    @action(methods=['GET'], detail=False, url_path='total-amounts')
    def get_wallet_amounts(self, request,):
        queryset = self.filter_queryset(self.get_queryset())
        return Response(
            queryset.aggregate(
                total_one_c=Sum('amount_1c', output_field=DecimalField(), default=Value(0.0)),
                total_crm=Sum('amount_crm', output_field=DecimalField(), default=Value(0.0)),
                total_paid=Sum('user__orders__price', filter=Q(user__orders__status="Оплачено"),
                               default=Value(0.0))
            )
        )


class BalanceHistoryViewSet(ManagerMixin, viewsets.ReadOnlyModelViewSet):
    queryset = BalancePlus.objects.all()
    serializer_class = CRMBalancePlusSerializer
    parser_classes = (parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser)
    pagination_class = AppPaginationClass
    filter_backends = (BalancePlusFilter,)

    def get_queryset(self):
        queryset = self.queryset.filter(dealer__city=self.request.user.staff_profile.city)
        return queryset


class BalancePlusView(ManagerMixin, generics.CreateAPIView):
    serializer_class = CRMBalancePlusCreateSerializer
