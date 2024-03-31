from django.db.models import Sum, Q, FloatField
from rest_framework import filters, generics, permissions, mixins, viewsets, decorators, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.models import DealerProfile, BalanceHistory, Wallet, MyUser
from crm_general.filters import FilterByFields
from crm_general.serializers import ActivitySerializer, UserImageSerializer
from crm_general.paginations import AppPaginationClass, ProductPagination, GeneralPurposePagination
from crm_general.utils import string_date_to_date, convert_bool_string_to_bool, today_on_true
from order.models import MyOrder, CartProduct, MainOrder
from product.models import ProductPrice, Collection, Category, AsiaProduct

from .mixins import BaseOrderMixin, BaseDealerViewMixin, BaseDealerRelationViewMixin, BaseManagerMixin
from .permissions import IsManager, ManagerOrderPermission
from .serializers import (
    MainShortOrderSerializer, MainOrderSerializer,
    DealerProfileListSerializer, DealerBirthdaySerializer, DealerProfileDetailSerializer,
    DealerBalanceHistorySerializer, DealerBasketProductSerializer,
    CollectionSerializer, ShortCategorySerializer, ProductDetailSerializer,
    WalletListSerializer, BalancePlusSerializer, ProductListForOrderSerializer,
    ShortProductSerializer, MainOrderUpdateSerializer
)
from ..models import CRMTask


# ---------------------------------------------------- ORDERS
class OrderListAPIView(BaseOrderMixin, generics.ListAPIView):
    queryset = (
        MainOrder.objects.select_related("author__village__city", "stock__city")
        .only("author__village__city", "stock__city", "id", "price", "type_status",
              "created_at", "paid_at", "is_active")
        .filter(is_active=True)
    )
    serializer_class = MainShortOrderSerializer
    pagination_class = GeneralPurposePagination
    filter_backends = (filters.SearchFilter, filters.OrderingFilter, FilterByFields)
    search_fields = ("author__user__name", "id")
    ordering_fields = ("id", "price", "created_at", "paid_at", "released_at")
    filter_by_fields = {
        "is_active": {"by": "is_active", "type": "boolean", "pipline": convert_bool_string_to_bool},
        "start_date": {"by": "created_at__date__gte", "type": "date", "pipline": string_date_to_date},
        "end_date": {"by": "created_at__date__lte", "type": "date", "pipline": string_date_to_date},
        "type_status": {"by": "type_status", "type": "string",
                        "addition_schema_params": {"enum": [order_status for order_status, _ in MyOrder.TYPE_STATUS]}},
        "status": {"by": "status", "type": "string",
                   "addition_schema_params": {"enum": [order_status for order_status, _ in MyOrder.STATUS]}},
        "user_id": {"by": "author__user__id", "type": "number"}
    }


class OrderRetrieveAPIView(BaseOrderMixin, generics.RetrieveAPIView):
    queryset = (
        MainOrder.objects.select_related("stock")
        .prefetch_related("receipts", "products")
        .only("id", "stock", "price", "status", "type_status",
              "created_at", "paid_at")
        .all()
    )
    serializer_class = MainOrderSerializer
    lookup_field = "id"
    lookup_url_kwarg = "order_id"


class OrderChangeActivityView(BaseOrderMixin, generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated, IsManager)
    queryset = MainOrder.objects.only("id", "is_active").all()
    serializer_class = ActivitySerializer
    lookup_field = "id"
    lookup_url_kwarg = "order_id"

    def patch(self, request, *args, **kwargs):
        order = self.get_object()
        order.is_active = not order.is_active
        order.save()
        serializer = self.get_serializer({"is_active": order.is_active}, many=False)
        return Response(serializer.data)


class OrderCreateAPIView(BaseOrderMixin, generics.CreateAPIView):
    """
    Create an order

    An object must be sent to the products_count field
    Where the keys are the product identifier and the value is the quantity
    """
    permission_classes = (permissions.IsAuthenticated, IsManager, ManagerOrderPermission)
    serializer_class = MainOrderSerializer


class OrderUpdateAPIView(BaseOrderMixin, generics.UpdateAPIView):
    permission_classes = (permissions.IsAuthenticated, IsManager)
    serializer_class = MainOrderUpdateSerializer


# -------------------------------------------------------- DEALERS
class DealerListViewSet(BaseDealerViewMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = (
        DealerProfile.objects.select_related("user", "village__city", "dealer_status")
        .prefetch_related("balance_histories", "orders")
        .only("user_id", "birthday", "village__city", "dealer_status")
        .all()
    )
    serializer_class = DealerProfileListSerializer
    pagination_class = AppPaginationClass
    filter_backends = (filters.SearchFilter, FilterByFields)
    search_fields = ("user__name", "user__id")
    filter_by_fields = {
        "start_date": {"by": "user__date_joined__date__gte", "type": "date", "pipline": string_date_to_date},
        "end_date": {"by": "user__date_joined__date__lte", "type": "date", "pipline": string_date_to_date},
        "status": {"by": "user__is_active", "type": "boolean", "pipline": convert_bool_string_to_bool},
        "dealer_status": {"by": "dealer_status_id", "type": "number"},
        "village__city_id": {"by": "city_id", "type": "number"}
    }
    lookup_field = "user_id"
    lookup_url_kwarg = "user_id"

    @decorators.action(['GET'], detail=False, url_path="amounts")
    def get_amounts(self, request):
        """
        Здесь нужно отправлять теже query что и в dealers
        """
        queryset = self.filter_queryset(self.get_queryset())
        amounts = queryset.aggregate(
            balance=Sum("wallet__amount_crm", output_field=FloatField())
        )
        return Response(amounts)

    # @decorators.action(["GET"], detail=True, url_path="saved-amount")
    # def get_saved_amount(self, request, user_id):
    #     start_date = request.query_params.get("start_date")
    #     end_date = request.query_params.get("end_date")
    #
    #     if not start_date or not end_date:
    #         return Response({"detail": "dates required in query!"}, status=status.HTTP_400_BAD_REQUEST)
    #
    #     dealer_profile = generics.get_object_or_404(self.get_queryset(), user_id=user_id)
    #     saved_amount = MyOrder.objects.filter(
    #         author=dealer_profile,
    #         is_active=True,
    #         status__in=("paid", "success", "sent"),
    #         paid_at__date__gte=string_date_to_date(start_date),
    #         paid_at__date__lte=string_date_to_date(end_date)
    #     ).aggregate(saved_amount=Sum("order_products__discount"))
    #     data = dict(saved_amount)
    #     data["current_balance_amount"] = dealer_profile.wallet.amount_crm
    #     return Response(data)


class DealerBirthdayListAPIView(BaseDealerViewMixin, generics.ListAPIView):
    queryset = (
        DealerProfile.objects.select_related("user", "village__city", "dealer_status")
        .only("user_id", "user", "birthday", "village__city", "dealer_status")
        .all()
    )
    serializer_class = DealerBirthdaySerializer
    pagination_class = AppPaginationClass
    filter_backends = (filters.SearchFilter, FilterByFields)
    search_fields = ("user__name",)
    filter_by_fields = {
        "start_date": {"by": "birthday__gte", "type": "date", "pipline": string_date_to_date},
        "end_date": {"by": "birthday__lte", "type": "date", "pipline": string_date_to_date}
    }


class DealerRetrieveAPIView(BaseDealerViewMixin, generics.RetrieveAPIView):
    queryset = (
        DealerProfile.objects.select_related("user", "village__city", "dealer_status")
        .prefetch_related("dealer_stores")
        .only("user", "birthday", "village__city", "dealer_status")
        .all()
    )
    serializer_class = DealerProfileDetailSerializer
    lookup_field = "user_id"


class DealerCreateAPIView(BaseDealerViewMixin, generics.CreateAPIView):
    serializer_class = DealerProfileDetailSerializer


class DealerUpdateAPIView(BaseDealerViewMixin, generics.UpdateAPIView):
    serializer_class = DealerProfileDetailSerializer
    lookup_field = "user_id"
    lookup_url_kwarg = "user_id"


class DealerChangeActivityView(BaseDealerViewMixin, generics.GenericAPIView):
    serializer_class = ActivitySerializer
    lookup_field = "user_id"
    lookup_url_kwarg = "user_id"

    def patch(self, request, *args, **kwargs):
        dealer = self.get_object()
        user = dealer.user
        user.is_active = not user.is_active
        user.save()
        serializer = self.get_serializer({"is_active": user.is_active}, many=False)
        return Response(serializer.data)


class DealerImageUpdateAPIView(BaseManagerMixin, generics.UpdateAPIView):
    queryset = MyUser.objects.filter(status="dealer")
    serializer_class = UserImageSerializer
    lookup_field = "id"
    lookup_url_kwarg = "user_id"

    def get_queryset(self):
        return super().get_queryset().filter(dealer_profile__managers=self.request.user.id)


class DealerBalanceHistoryListAPIView(BaseDealerRelationViewMixin, generics.ListAPIView):
    queryset = (
        BalanceHistory.objects.only("id", "created_at", "status", "amount", "balance")
        .all()
    )
    serializer_class = DealerBalanceHistorySerializer
    filter_backends = (FilterByFields,)
    filter_by_fields = {
        "start_date": {"by": "created_at__date__gte", "type": "date", "pipline": string_date_to_date},
        "end_date": {"by": "created_at__date__lte", "type": "date", "pipline": string_date_to_date}
    }
    lookup_field = "user_id"
    lookup_url_kwarg = "user_id"

    def get_queryset(self):
        dealer_profile = self.get_dealer_profile()
        return super().get_queryset().filter(dealer=dealer_profile)


class DealerBasketListAPIView(BaseDealerRelationViewMixin, generics.ListAPIView):
    queryset = (
        CartProduct.objects.select_related("product", "cart")
        .all()
    )
    serializer_class = DealerBasketProductSerializer
    filter_backends = (filters.SearchFilter, FilterByFields)
    search_fields = ("product__title",)
    filter_by_fields = {
        "start_date": {"by": "created_at__date__gte", "type": "date", "pipline": string_date_to_date},
        "end_date": {"by": "created_at__date__lte", "type": "date", "pipline": string_date_to_date}
    }

    def get_queryset(self):
        dealer = self.get_dealer_profile()
        return super().get_queryset().filter(cart__dealer=dealer)


# --------------------------------------------------------- PRODUCTS
class CollectionListAPIView(BaseManagerMixin, generics.ListAPIView):
    queryset = (
        Collection.objects.defer("id").all()
    )
    serializer_class = CollectionSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ("title",)


class CategoryListAPIView(BaseManagerMixin, generics.ListAPIView):
    queryset = (
        Category.objects.only("slug", "title", "is_active")
        .all().distinct()
    )
    serializer_class = ShortCategorySerializer
    filter_backends = (filters.SearchFilter, FilterByFields)
    search_fields = ("title",)
    filter_by_fields = {
        "collection_slug": {"by": "products__collection__slug", "type": "string"}
    }


class ProductPriceListAPIView(BaseManagerMixin, generics.ListAPIView):
    queryset = (
        AsiaProduct.objects.all()
    )
    serializer_class = ShortProductSerializer
    filter_backends = (filters.SearchFilter, FilterByFields)
    search_fields = ("title",)
    filter_by_fields = {
        "is_active": {"by": "is_active", "type": "boolean", "pipline": convert_bool_string_to_bool},
        "category_slug": {"by": "category__slug", "type": "string"},
        "collection_slug": {"by": "collection__slug", "type": "string"},
        "city_id": {"by": "city_id", "type": "number"}
    }


class ProductRetrieveAPIView(BaseManagerMixin, generics.RetrieveAPIView):
    queryset = (
        AsiaProduct.objects.select_related("collection")
        .prefetch_related("images", "sizes")
        .only("id", "diagram", "title", "vendor_code", "description", "collection__title",
              "weight", "package_count", "made_in", "created_at", "updated_at")
        .all()
    )
    serializer_class = ProductDetailSerializer
    lookup_field = "id"
    lookup_url_kwarg = "product_id"


# ----------------------------------------------- BALANCES
class BalanceViewSet(BaseManagerMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = (
        Wallet.objects.select_related("dealer")
        .only("id", "dealer", "amount_1c", "amount_crm")
        .filter(Q(amount_crm__gt=0) | Q(amount_1c__gt=0))
    )
    dealers_queryset = DealerProfile.objects.all()
    serializer_class = WalletListSerializer
    pagination_class = AppPaginationClass
    filter_backends = (filters.SearchFilter, FilterByFields, filters.OrderingFilter)
    search_fields = ("dealer__user__name",)
    filter_by_fields = {
        "start_date": {"by": "dealer__balance_histories__created_at__date__gte", "type": "date",
                       "pipline": string_date_to_date},
        "end_date": {"by": "dealer__balance_histories__created_at__date__lte", "type": "date",
                     "pipline": string_date_to_date},
        "status": {"by": "dealer__dealer_status_id", "type": "number"}
    }
    ordering_fields = ("amount_1c", "amount_crm")

    def get_queryset(self):
        return super().get_queryset().filter(dealer__managers=self.request.user.id).distinct()

    @decorators.action(["GET"], detail=False, url_path="amounts")
    def get_amounts(self, request):
        """
        Необходимо отправлять те же параметры query что и у balances
        """
        queryset = self.filter_queryset(self.get_queryset())
        amounts = queryset.aggregate(
            amount_1c=Sum("amount_1c"),
            amount_crm=Sum("amount_crm"),
            paid_amount=Sum(
                "dealer__orders__price",
                filter=Q(
                    dealer__orders__is_active=True,
                    dealer__orders__paid_at__isnull=False
                )
            )
        )
        return Response(amounts)

    @decorators.action(["GET"], detail=False, url_path=r"(?P<user_id>.+)/saved-amount")
    def get_saved_amount(self, request, user_id):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not start_date or not end_date:
            return Response({"detail": "dates required in query!"}, status=status.HTTP_400_BAD_REQUEST)

        dealers_queryset = self.dealers_queryset.filter(managers=request.user.id)
        dealer_profile = generics.get_object_or_404(dealers_queryset, user_id=user_id)
        saved_amount = MyOrder.objects.filter(
            author=dealer_profile,
            is_active=True,
            status__in=("paid", "success", "sent"),
            paid_at__date__gte=string_date_to_date(start_date),
            paid_at__date__lte=string_date_to_date(end_date)
        ).aggregate(saved_amount=Sum("order_products__discount"))
        data = dict(saved_amount)
        data["current_balance_amount"] = dealer_profile.wallet.amount_crm
        return Response(data)


class BalancePlusManagerView(BaseManagerMixin, generics.CreateAPIView):
    serializer_class = BalancePlusSerializer


class ProdListForOrderView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

    def get(self, request):
        serializer = ProductListForOrderSerializer(AsiaProduct.objects.filter(is_active=True),
                                                   many=True, context=self.get_renderer_context()).data
        return Response(serializer, status=status.HTTP_200_OK)


class ManagerDeleteOrderView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

    def post(self, request):
        order_id = request.data.get('order_id')
        order = MyOrder.objects.get(id=order_id)
        manager = request.user
        if manager in order.author.managers.all():
            if order.status == 'created':
                order.delete()
            elif order.status == 'paid' and order.type_status == 'wallet':
                order.delete()

            return Response({'text': 'Success!'}, status=status.HTTP_200_OK)
        return Response({'text': 'Permission denied!'}, status=status.HTTP_400_BAD_REQUEST)


class ManagerNotificationView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

    def get(self, request):
        user = self.request.user
        tasks_count = CRMTask.objects.filter(status='created', executors=user).count()

        data = {
            'tasks_count': tasks_count
        }

        return Response(data, status=status.HTTP_200_OK)
