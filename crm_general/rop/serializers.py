from decimal import Decimal
from datetime import date, datetime

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import DecimalField, FloatField, Sum, Count, Q, Value
from django.db.models.functions import Round
from django.utils import timezone
from rest_framework import serializers

from account.models import ManagerProfile, DealerProfile, DealerStatus, Wallet, DealerStore

from crm_general.serializers import BaseProfileSerializer
from crm_general.utils import get_motivation_done
from general_service.models import City, PriceType
from general_service.serializers import CitySerializer
from order.models import CartProduct, MyOrder
from product.models import Collection, Category, AsiaProduct, ProductPrice, ProductImage, ProductSize


class ManagerProfileSerializer(BaseProfileSerializer):
    city = CitySerializer(many=False, read_only=True)
    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        write_only=True,
        required=True
    )

    class Meta:
        model = ManagerProfile
        fields = ("user", "city", "city_id", 'is_main')
        user_status = "manager"

    def validate(self, attrs):
        city = attrs.pop("city_id", None)
        rop_profile = self.context["view"].rop_profile
        if city and not rop_profile.cities.filter(id=city.id).exists():
            raise serializers.ValidationError({"city_id": "Данный город вам недоступен"})
        if city:
            attrs["city"] = city
        return attrs


class DealerStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerStatus
        fields = ("id", "title", "discount")


class DealerProfileListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField(read_only=True)
    incoming_funds = serializers.SerializerMethodField(read_only=True)
    shipment_amount = serializers.SerializerMethodField(read_only=True)
    last_order_date = serializers.SerializerMethodField(read_only=True)
    balance_amount = serializers.SerializerMethodField(read_only=True)
    dealer_status = DealerStatusSerializer(many=False, read_only=True)
    status = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DealerProfile
        fields = ("id", "name", "incoming_funds", "shipment_amount", "dealer_status", "last_order_date",
                  "balance_amount", "status", 'village')
        extra_kwargs = {"id": {"source": "user_id", "read_only": True}}

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['village__title'] = instance.village.title if instance.village else None
        rep['is_active'] = instance.user.is_active
        return rep

    def get_name(self, instance):
        return instance.user.name

    def get_balance_amount(self, instance) -> Decimal:
        try:
            return instance.wallet.amount_crm
        except ObjectDoesNotExist:
            return 0.0

    def get_incoming_funds(self, instance) -> Decimal:
        return Decimal(sum(instance.user.money_docs.filter(is_active=True).values_list('amount', flat=True)))

    def get_shipment_amount(self, instance) -> Decimal:
        return Decimal(sum(instance.orders.filter(
            is_active=True, status__in=['sent', 'success']
        ).values_list('price', flat=True)))

    def get_last_order_date(self, instance) -> date | None:
        last_order = instance.orders.only("created_at").order_by("-created_at").first()
        if last_order:
            return last_order.created_at.date()

    def get_status(self, instance) -> bool:
        return instance.wallet.amount_crm > 50000


class ShortWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = "__all__"


class DealerStoreSerializer(serializers.ModelSerializer):
    city = CitySerializer(many=False, read_only=True)

    class Meta:
        model = DealerStore
        fields = ("id", "city", "title", "address")
        extra_kwargs = {
            "title": {"read_only": True},
            "address": {"read_only": True}
        }


class PriceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceType
        fields = "__all__"


class DealerProfileDetailSerializer(BaseProfileSerializer):
    wallet = ShortWalletSerializer(many=False, read_only=True)
    dealer_status = DealerStatusSerializer(many=False, read_only=True)
    stores = DealerStoreSerializer(many=True, source="dealer_stores", read_only=True)
    dealer_status_id = serializers.PrimaryKeyRelatedField(
        queryset=DealerStatus.objects.all(),
        write_only=True,
        required=True
    )
    city = CitySerializer(many=False, read_only=True)
    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        write_only=True,
        required=True
    )
    price_type = PriceTypeSerializer(many=False, read_only=True)
    price_type_id = serializers.PrimaryKeyRelatedField(
        queryset=PriceType.objects.all(),
        write_only=True,
        required=True
    )
    liability = serializers.IntegerField(required=True)
    motivations = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DealerProfile
        fields = ("user", "liability", "address", "birthday", "city", "dealer_status", "wallet", "stores",
                  "price_type", "dealer_status_id", "city_id", "price_type_id", "motivations", 'village')
        user_status = "dealer"

    def get_motivations(self, instance):
        return get_motivation_done(instance)

    def validate(self, attrs):
        price_type = attrs.pop("price_type_id", None)
        if price_type:
            attrs["price_type"] = price_type

        dealer_status = attrs.pop("dealer_status_id", None)
        if dealer_status:
            attrs["dealer_status"] = dealer_status

        return attrs


class DealerBasketProductSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField(read_only=True)
    amount = serializers.SerializerMethodField(read_only=True)
    discount = serializers.SerializerMethodField(read_only=True)
    stock_count = serializers.SerializerMethodField(read_only=True)
    stock_city = serializers.SerializerMethodField(read_only=True)
    stock_name = serializers.SerializerMethodField(read_only=True)
    stock_address = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CartProduct
        fields = ("id", "product_name", "count", "amount", "discount", "stock_city", "stock_count",
                  "stock_name", "stock_address")
        extra_kwargs = {"id": {"read_only": True, "source": "cart_id"}}

    def get_product_name(self, instance) -> str:
        return instance.product.title

    def get_amount(self, instance) -> float:
        product_price = instance.product.prices.filter(
            city=instance.cart.dealer.city,
            d_status=instance.cart.dealer.dealer_status
        ).first()

        if product_price:
            return product_price.price * instance.count
        return 0.0

    def get_discount(self, instance) -> dict[str, float | str] | None:
        product_price = instance.product.prices.filter(
            city=instance.cart.dealer.city,
            d_status=instance.cart.dealer.dealer_status
        ).first()

        if product_price:
            return {
                "amount": product_price.discount,
                "type": product_price.discount_status
            }

    def get_stock_city(self, instance) -> str:
        if instance.cart.stock.city:
            return instance.cart.stock.city.title

    def get_stock_count(self, instance) -> int:
        stock_count = instance.cart.stock.counts.filter(product=instance.product).first()
        return stock_count.count_crm if stock_count else 0

    def get_stock_name(self, instance) -> str:
        return instance.cart.stock.title

    def get_stock_address(self, instance) -> str:
        return instance.cart.stock.address


# --------------------------------------------------- ORDER
class ShortOrderSerializer(serializers.ModelSerializer):
    dealer_city = serializers.SerializerMethodField(read_only=True)
    stock_city = serializers.SerializerMethodField(read_only=True)
    stock_name = serializers.SerializerMethodField(read_only=True)
    stock_address = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MyOrder
        fields = ("id", "name", "dealer_city", "stock_city", "price", "type_status",
                  "created_at", "paid_at", "released_at", "is_active", "stock_name", "stock_address")

    def get_dealer_city(self, instance):
        if instance.author:
            return instance.author.city.title

    def get_stock_city(self, instance):
        if instance.stock:
            return instance.stock.city.title

    def get_stock_name(self, instance):
        if instance.stock:
            return instance.stock.title

    def get_stock_address(self, instance):
        if instance.stock:
            return instance.stock.address


# ----------------------------------------------- PRODUCT
class CollectionSerializer(serializers.ModelSerializer):
    categories_count = serializers.SerializerMethodField(read_only=True)
    products_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Collection
        fields = ("slug", "title", "categories_count", "products_count")

    def get_categories_count(self, instance):
        return instance.products.aggregate(
            categories_count=Count("category_id", distinct=True)
        )["categories_count"]

    def get_products_count(self, instance):
        return instance.products.count()


class ShortCategorySerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Category
        fields = ("slug", "title", "products_count", "is_active")

    def get_products_count(self, instance):
        return instance.products.count()


class ShortProductSerializer(serializers.ModelSerializer):
    collection = serializers.SerializerMethodField(read_only=True)
    category = serializers.SerializerMethodField(read_only=True)
    avg_receipt_amount = serializers.SerializerMethodField(read_only=True)
    last_fifteen_days_ratio = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AsiaProduct
        fields = ("id", "title", "vendor_code", "collection", "category", "is_discount", "is_active",
                  "last_fifteen_days_ratio", "avg_receipt_amount", "created_at")

    def get_collection(self, instance):
        return instance.collection.title

    def get_category(self, instance):
        return instance.category.title

    def get_last_fifteen_days_ratio(self, instance):
        naive_time = timezone.localtime().now()
        today = timezone.make_aware(naive_time)
        fifteen_days_ago = today - timezone.timedelta(days=15)
        return instance.order_products.aggregate(
            last_fifteen_days_ratio=Round(
                Sum(
                    "count",
                    filter=Q(
                        order__is_active=True,
                        order__created_at__gte=fifteen_days_ago,
                        order__status__in=('sent', 'paid', 'success')
                    ),
                    output_field=FloatField()
                ) / Value(15),
                precision=2
            )
        )["last_fifteen_days_ratio"]

    def get_avg_receipt_amount(self, instance):
        return instance.order_products.aggregate(
            avg_receipt_amount=Sum("total_price") / Sum("count")
        )["avg_receipt_amount"]


class ProductPriceListSerializer(serializers.ModelSerializer):
    product = ShortProductSerializer(read_only=True, many=False)
    stock_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProductPrice
        fields = ("product", "price", "stock_count")

    def get_stock_count(self, instance):
        return instance.product.counts.filter(stock__city=instance.city).aggregate(
            stock_count=Sum("count_crm")
        )['stock_count']


class ProductSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSize
        fields = ("title", "length", "width", "height")


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "position")


class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True)
    sizes = ProductSizeSerializer(many=True)
    collection = serializers.SlugRelatedField(slug_field="title", read_only=True)

    class Meta:
        model = AsiaProduct
        fields = ("id", "images", "diagram", "title", "vendor_code", "description", "sizes", "collection",
                  "weight", "package_count", "made_in", "created_at", "updated_at")


# ------------------------------------------------- BALANCES
class WalletListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField(read_only=True)
    paid_amount = serializers.SerializerMethodField(read_only=True)
    city = serializers.SerializerMethodField(read_only=True)
    status = serializers.SerializerMethodField(read_only=True)
    last_replenishment_date = serializers.SerializerMethodField(read_only=True)
    user_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Wallet
        fields = ("id", "user_id", "name", "amount_1c", "paid_amount", "amount_crm", "city", "status",
                  "last_replenishment_date")

    def get_user_id(self, instance):
        return instance.dealer.user.id

    def get_name(self, instance):
        return instance.dealer.user.name

    def get_paid_amount(self, instance) -> float:
        return instance.dealer.orders.filter(is_active=True, paid_at__isnull=False).aggregate(
            amount=Round(Sum("price", output_field=FloatField()), precision=2)
        )["amount"]

    def get_city(self, instance):
        return instance.dealer.village.city.title

    def get_status(self, instance):
        return instance.dealer.dealer_status.title

    def get_last_replenishment_date(self, instance) -> datetime:
        last_replenishment = instance.dealer.user.money_docs.filter(is_active=True).last()
        if last_replenishment:
            return last_replenishment.created_at


class ManagerListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ManagerProfile
        fields = ('user', 'city', 'name')

    def get_name(self, instance):
        return instance.user.name
