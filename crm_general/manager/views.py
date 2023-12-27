from django.db.models import F, Sum, Q, FloatField
from rest_framework import filters, generics, permissions, mixins, viewsets, decorators, status
from rest_framework.response import Response

from account.models import DealerProfile, BalanceHistory, Wallet, MyUser
from crm_general.filters import FilterByFields
from crm_general.serializers import ActivitySerializer, UserImageSerializer, CRMTaskResponseSerializer
from crm_general.paginations import AppPaginationClass
from crm_general.utils import string_date_to_date, convert_bool_string_to_bool, today_on_true
from order.models import MyOrder, CartProduct, ReturnOrder
from product.models import ProductPrice, Collection, Category, AsiaProduct

from .mixins import BaseOrderMixin, BaseDealerViewMixin, BaseDealerRelationViewMixin, BaseManagerMixin
from .permissions import IsManager, ManagerOrderPermission
from .serializers import (
    ShortOrderSerializer, OrderSerializer,
    DealerProfileListSerializer, DealerBirthdaySerializer, DealerProfileDetailSerializer,
    DealerBalanceHistorySerializer, DealerBasketProductSerializer,
    ProductPriceListSerializer, CollectionSerializer, ShortCategorySerializer, ProductDetailSerializer,
    WalletListSerializer,
    ReturnOrderListSerializer, ReturnOrderDetailSerializer, BalancePlusSerializer, ManagerTaskListSerializer
)


# ---------------------------------------------------- ORDERS
class OrderListAPIView(BaseOrderMixin, generics.ListAPIView):
    queryset = (
        MyOrder.objects.select_related("author__city", "stock__city")
                       .only("author__city", "stock__city", "id", "name", "price", "type_status",
                             "created_at", "paid_at", "released_at", "is_active")
                       .all()
    )
    serializer_class = ShortOrderSerializer
    pagination_class = AppPaginationClass
    filter_backends = (filters.SearchFilter, filters.OrderingFilter, FilterByFields)
    search_fields = ("name", "id")
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
        MyOrder.objects.select_related("stock")
                       .prefetch_related("order_receipts", "order_products")
                       .only("id", "name", "gmail", "phone", "address", "stock", "price", "status", "type_status",
                             "comment", "created_at", "released_at", "paid_at")
                       .all()
    )
    serializer_class = OrderSerializer
    lookup_field = "id"
    lookup_url_kwarg = "order_id"


class OrderChangeActivityView(BaseOrderMixin, generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated, IsManager)
    queryset = MyOrder.objects.only("id", "is_active").all()
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
    serializer_class = OrderSerializer


# -------------------------------------------------------- DEALERS
class DealerListViewSet(BaseDealerViewMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = (
        DealerProfile.objects.select_related("user", "city", "dealer_status")
                             .prefetch_related("balance_histories", "orders")
                             .only("user_id", "birthday", "city", "dealer_status")
                             .all()
    )
    serializer_class = DealerProfileListSerializer
    pagination_class = AppPaginationClass
    filter_backends = (filters.SearchFilter, FilterByFields)
    search_fields = ("user__name", "user__id")
    filter_by_fields = {
        "start_date": {"by": "user__date_joined__date__gte", "type": "date", "pipline": string_date_to_date},
        "end_date": {"by": "user__date_joined__date__lte", "type": "date", "pipline": string_date_to_date},
        "status": {"by": "dealer_status_id", "type": "number"}
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
            incoming_funds=Sum(
                "balance_histories__amount",
                filter=Q(balance_histories__status="wallet"),
                output_field=FloatField()
            ),
            shipment_amount=Sum(
                "balance_histories__amount",
                filter=Q(balance_histories__status="order"),
                output_field=FloatField()
            ),
            balance=F("wallet__amount_crm")
        )
        return Response(amounts)

    @decorators.action(["GET"], detail=True, url_path="saved-amount")
    def get_saved_amount(self, request, user_id):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not start_date or not end_date:
            return Response({"detail": "dates required in query!"}, status=status.HTTP_400_BAD_REQUEST)

        dealer_profile = generics.get_object_or_404(self.get_queryset(), user_id=user_id)
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


class DealerBirthdayListAPIView(BaseDealerViewMixin, generics.ListAPIView):
    queryset = (
        DealerProfile.objects.select_related("user", "city", "dealer_status")
                             .only("user_id", "user", "birthday", "city", "dealer_status")
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
        DealerProfile.objects.select_related("user", "city", "dealer_status")
                             .prefetch_related("dealer_stores")
                             .only("user", "birthday", "city", "dealer_status")
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
        return super().get_queryset().filter(dealer_profile__city=self.manager_profile.city)


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
    pagination_class = AppPaginationClass
    filter_backends = (filters.SearchFilter, FilterByFields)
    search_fields = ("title",)
    filter_by_fields = {
        "collection_slug": {"by": "products__collection__slug", "type": "string"}
    }


class ProductPriceListAPIView(BaseManagerMixin, generics.ListAPIView):
    queryset = (
        ProductPrice.objects.select_related("product")
                            .only("product", "price")
                            .all()
    )
    serializer_class = ProductPriceListSerializer
    pagination_class = AppPaginationClass
    filter_backends = (filters.SearchFilter, FilterByFields)
    search_fields = ("product__name",)
    filter_by_fields = {
        "is_active": {"by": "product__is_active", "type": "boolean", "pipline": convert_bool_string_to_bool},
        "category_slug": {"by": "product__category__slug", "type": "string"}
    }

    def get_queryset(self):
        return super().get_queryset().filter(city=self.manager_profile.city)


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
                      .all()
    )
    dealers_queryset = DealerProfile.objects.all()
    serializer_class = WalletListSerializer
    pagination_class = AppPaginationClass
    filter_backends = (filters.SearchFilter, FilterByFields)
    search_fields = ("dealer__user__name",)
    filter_by_fields = {
        "start_date": {"by": "dealer__balance_histories__created_at__date__gte", "type": "date",
                       "pipline": string_date_to_date},
        "end_date": {"by": "dealer__balance_histories__created_at__date__lte", "type": "date",
                     "pipline": string_date_to_date},
    }

    def get_queryset(self):
        return super().get_queryset().filter(dealer__city=self.manager_profile.city).distinct()

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

        dealers_queryset = self.dealers_queryset.filter(city=self.manager_profile.city)
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


# ---------------------------------------- RETURNS
class ReturnListAPIView(BaseManagerMixin, generics.ListAPIView):
    queryset = (
        ReturnOrder.objects.select_related("order")
                           .only("id", "order", "status", "moder_comment")
                           .all()
    )
    serializer_class = ReturnOrderListSerializer
    pagination_class = AppPaginationClass
    filter_backends = (filters.SearchFilter, FilterByFields)
    search_fields = ("order__name", "order__email")
    filter_by_fields = {
        "status": {"by": "status", "type": "string", "addition_schema_params": {
            "enum": [ro_status for ro_status, _ in ReturnOrder.STATUS]
        }},
        "start_date": {"by": "created_at__date__gte", "type": "date", "pipline": string_date_to_date},
        "end_date": {"by": "created_at__date__lte", "type": "date", "pipline": string_date_to_date},
    }

    def get_queryset(self):
        return super().get_queryset().filter(order__author__city=self.manager_profile.city)


class ReturnRetrieveAPIView(BaseManagerMixin, generics.RetrieveAPIView):
    queryset = ReturnOrder.objects.all()
    serializer_class = ReturnOrderDetailSerializer
    lookup_field = "id"
    lookup_url_kwarg = "return_id"

    def get_queryset(self):
        return super().get_queryset().filter(order__author__city=self.manager_profile.city)


class ReturnUpdateAPIView(BaseManagerMixin, generics.UpdateAPIView):
    queryset = ReturnOrder.objects.all()
    serializer_class = ReturnOrderDetailSerializer
    lookup_field = "id"
    lookup_url_kwarg = "return_id"

    def get_queryset(self):
        return super().get_queryset().filter(order__author__city=self.manager_profile.city)


# ---------------------------------------- TASKS
class ManagerTaskListAPIView(BaseManagerMixin, generics.ListAPIView):
    serializer_class = ManagerTaskListSerializer
    filter_backends = (filters.SearchFilter, FilterByFields, filters.OrderingFilter)
    search_fields = ("title",)
    filter_by_fields = {
        "start_date": {"by": "task__created_at__date__gte", "type": "date", "pipline": string_date_to_date},
        "end_date": {"by": "task__created_at__date__lte", "type": "date", "pipline": string_date_to_date},
        "overdue": {"by": "task__end_date__lte", "type": "boolean", "pipline": today_on_true},
        "is_done": {"by": "is_done", "type": "boolean", "pipline": convert_bool_string_to_bool}
    }
    ordering_fields = ("title", "updated_at", "created_at", "end_date")

    def get_queryset(self):
        return (
            self.request.user.task_responses
            .select_related("task")
            .only("id", "task", "grade", "is_done")
            .filter(task__is_active=True)
        )


class ManagerTaskRetrieveAPIView(BaseManagerMixin, generics.RetrieveAPIView):
    serializer_class = CRMTaskResponseSerializer
    lookup_field = "id"
    lookup_url_kwarg = "response_task_id"

    def get_queryset(self):
        return (
            self.request.user.task_responses
            .select_related("task")
            .only("id", "task", "grade", "is_done")
            .filter(task__is_active=True)
        )


class ManagerTaskUpdateAPIView(BaseManagerMixin, generics.UpdateAPIView):
    serializer_class = CRMTaskResponseSerializer
    lookup_field = "id"
    lookup_url_kwarg = "response_task_id"

    def get_queryset(self):
        return (
            self.request.user.task_responses
            .select_related("task")
            .prefetch_related("response_files")
            .only("id", "task", "grade", "is_done")
            .filter(task__is_active=True)
        )
