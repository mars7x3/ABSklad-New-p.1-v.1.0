from django.db.models import FloatField, Sum, Q
from rest_framework import decorators, filters, mixins, generics, viewsets, status
from rest_framework.response import Response

from account.models import ManagerProfile, DealerProfile, BalanceHistory, Wallet, DealerStatus
from crm_general.filters import FilterByFields
from crm_general.paginations import AppPaginationClass
from crm_general.serializers import ActivitySerializer
from crm_general.utils import convert_bool_string_to_bool, string_date_to_date
from order.models import CartProduct, MyOrder
from product.models import Collection, Category, ProductPrice, AsiaProduct

from .serializers import ManagerProfileSerializer, DealerProfileListSerializer, DealerProfileDetailSerializer, \
    DealerBalanceHistorySerializer, DealerBasketProductSerializer, ShortOrderSerializer, CollectionSerializer, \
    ShortCategorySerializer, ProductPriceListSerializer, ProductDetailSerializer, WalletListSerializer, \
    DealerStatusSerializer
from .mixins import BaseRopMixin, BaseDealerRelationViewMixin, BaseDealerMixin


# -------------------------------------------- MANAGERS
class ManagerListAPIView(BaseRopMixin, generics.ListAPIView):
    queryset = ManagerProfile.objects.select_related("user", "city").all()
    serializer_class = ManagerProfileSerializer
    pagination_class = AppPaginationClass
    filter_backends = (filters.SearchFilter, FilterByFields)
    search_fields = ("user__name",)
    filter_by_fields = {
        "is_active": {"by": "user__is_active", "type": "boolean", "pipline": convert_bool_string_to_bool},
        "start_date": {"by": "user__joined_at__date__gte", "type": "date", "pipline": string_date_to_date},
        "end_date": {"by": "user__joined_at__date__gte", "type": "date", "pipline": string_date_to_date},
        "city_slug": {"by": "city__slug", "type": "string"}
    }

    def get_queryset(self):
        return super().get_queryset().filter(city__in=self.rop_profile.cities.all())


class ManagerRetrieveAPIView(BaseRopMixin, generics.RetrieveAPIView):
    queryset = ManagerProfile.objects.select_related("user", "city").all()
    serializer_class = ManagerProfileSerializer
    lookup_field = "user_id"
    lookup_url_kwarg = "user_id"


class ManagerCreateAPIView(BaseRopMixin, generics.CreateAPIView):
    serializer_class = ManagerProfileSerializer


# -------------------------------------------- DEALERS
class DealerListViewSet(BaseRopMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = DealerProfile.objects.all()
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

    def get_queryset(self):
        return super().get_queryset().filter(city__in=self.rop_profile.cities.all())

    @decorators.action(['GET'], detail=False, url_path="amounts")
    def get_amounts(self, request):
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
            )
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


class DealerRetrieveAPIView(BaseRopMixin, generics.RetrieveAPIView):
    queryset = DealerProfile.objects.all()
    serializer_class = DealerProfileDetailSerializer
    lookup_field = "user_id"
    lookup_url_kwarg = "user_id"


class DealerBalanceHistoryListAPIView(BaseDealerRelationViewMixin, generics.ListAPIView):
    queryset = BalanceHistory.objects.all()
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
    queryset = CartProduct.objects.select_related("product", "cart").all()
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


class OrderListAPIView(BaseRopMixin, generics.ListAPIView):
    queryset = (
        MyOrder.objects.select_related("author", "stock")
                       .only("author", "stock", "id", "name", "price", "type_status",
                             "created_at", "paid_at", "released_at", "is_active")
                       .all()
    )
    serializer_class = ShortOrderSerializer
    pagination_class = AppPaginationClass
    filter_backends = (filters.SearchFilter, filters.OrderingFilter,)
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

    def get_queryset(self):
        return super().get_queryset().filter(author__city_id__in=self.rop_profile.cities.all())


class DealerChangeActivityView(BaseDealerMixin, generics.GenericAPIView):
    serializer_class = ActivitySerializer

    def patch(self, request, *args, **kwargs):
        dealer = self.get_object()
        user = dealer.user
        user.is_active = not user.is_active
        user.save()
        serializer = self.get_serializer({"is_active": user.is_active}, many=False)
        return Response(serializer.data)


class DealerCreateAPIView(BaseDealerMixin, generics.CreateAPIView):
    serializer_class = DealerProfileDetailSerializer


class DealerUpdateAPIView(BaseDealerMixin, generics.UpdateAPIView):
    serializer_class = DealerProfileDetailSerializer


class DealerStatusListAPIView(BaseRopMixin, generics.ListAPIView):
    queryset = DealerStatus.objects.all()
    serializer_class = DealerStatusSerializer


class DealerStatusCreateAPIView(BaseRopMixin, generics.CreateAPIView):
    serializer_class = DealerStatusSerializer


class DealerStatusUpdateAPIView(BaseRopMixin, generics.UpdateAPIView):
    queryset = DealerStatus.objects.all()
    serializer_class = DealerStatusSerializer
    lookup_field = "id"
    lookup_url_kwarg = "status_id"


# ------------------------------------------------- PRODUCTS
class CollectionListAPIView(BaseRopMixin, generics.ListAPIView):
    queryset = Collection.objects.only("slug", "title").all()
    serializer_class = CollectionSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ("title",)


class CategoryListAPIView(BaseRopMixin, generics.ListAPIView):
    queryset = Category.objects.only("slug", "title", "is_active").all()
    serializer_class = ShortCategorySerializer
    pagination_class = AppPaginationClass
    filter_backends = (filters.SearchFilter, FilterByFields)
    search_fields = ("title",)
    filter_by_fields = {
        "collection_slug": {"by": "products__collection__slug", "type": "string"}
    }


class ProductPriceListAPIView(BaseRopMixin, generics.ListAPIView):
    queryset = ProductPrice.objects.select_related("product").only("product", "price").all()
    serializer_class = ProductPriceListSerializer
    pagination_class = AppPaginationClass
    filter_backends = (filters.SearchFilter, FilterByFields)
    search_fields = ("product__name",)
    filter_by_fields = {
        "is_active": {"by": "product__is_active", "type": "boolean", "pipline": convert_bool_string_to_bool},
        "category_slug": {"by": "product__category__slug", "type": "string"}
    }

    def get_queryset(self):
        return super().get_queryset().filter(city__in=self.rop_profile.cities.all())


class ProductRetrieveAPIView(BaseRopMixin, generics.RetrieveAPIView):
    queryset = (
        AsiaProduct.objects.select_related("collection")
                           .prefetch_related("images", "sizes")
                           .only("id", "diagram", "title", "vendor_code", "description", "collection",
                                 "weight", "package_count", "made_in", "created_at", "updated_at")
                           .all()
    )
    serializer_class = ProductDetailSerializer
    lookup_field = "id"
    lookup_url_kwarg = "product_id"


# ----------------------------------------------- BALANCES
class BalanceViewSet(BaseRopMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = (
        Wallet.objects.select_related("dealer")
                      .only("id", "dealer", "amount_1c", "amount_crm")
                      .all()
    )
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
        return super().get_queryset().filter(dealer__city_id__in=self.rop_profile.cities.all())

    @decorators.action(["GET"], detail=False, url_path="amounts")
    def get_amounts(self, request):
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
