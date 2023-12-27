from decimal import Decimal
from datetime import date, datetime

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import DecimalField, FloatField, Sum, Count, Q, Value
from django.db.models.functions import Round
from django.utils import timezone
from rest_framework import serializers

from account.models import ManagerProfile, DealerProfile, DealerStatus, Wallet, DealerStore, BalanceHistory
from crm_general.models import CRMTask, CRMTaskResponse, CRMTaskFile, CRMTaskResponseFile
from crm_general.serializers import BaseProfileSerializer
from general_service.models import City
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
        fields = ("user", "city", "city_id")
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
    city = CitySerializer(many=False, read_only=True)
    incoming_funds = serializers.SerializerMethodField(read_only=True)
    shipment_amount = serializers.SerializerMethodField(read_only=True)
    last_order_date = serializers.SerializerMethodField(read_only=True)
    balance_amount = serializers.SerializerMethodField(read_only=True)
    dealer_status = DealerStatusSerializer(many=False, read_only=True)
    status = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DealerProfile
        fields = ("id", "name", "incoming_funds", "shipment_amount", "city", "dealer_status", "last_order_date",
                  "balance_amount", "status")
        extra_kwargs = {"id": {"source": "user_id", "read_only": True}}

    def get_name(self, instance):
        return instance.user.name

    def get_balance_amount(self, instance) -> Decimal:
        try:
            return instance.wallet.amount_crm
        except ObjectDoesNotExist:
            return 0.0

    def get_incoming_funds(self, instance) -> Decimal:
        return instance.balance_histories.only("amount").filter(status="wallet").aggregate(
            incoming_funds=Sum("amount", output_field=DecimalField(max_digits=100, decimal_places=2))
        )["incoming_funds"]

    def get_shipment_amount(self, instance) -> Decimal:
        return instance.balance_histories.only("amount").filter(status="order").aggregate(
            shipment_amount=Sum("amount", output_field=DecimalField(max_digits=100, decimal_places=2))
        )["shipment_amount"]

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
    price_city = CitySerializer(many=False, read_only=True)
    price_city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        write_only=True,
        required=True
    )
    liability = serializers.IntegerField(required=True)

    class Meta:
        model = DealerProfile
        fields = ("user", "liability", "address", "birthday", "city", "dealer_status", "wallet", "stores",
                  "price_city", "dealer_status_id", "city_id", "price_city_id")
        user_status = "dealer"

    def validate(self, attrs):
        rop_profile = self.context['view'].rop_profile

        city = attrs.pop("city_id", None)
        if city and not rop_profile.cities.filter(id=city.id).exists():
            raise serializers.ValidationError({"city_id": "Данный город не поддерживается или вам не доступен"})

        if city:
            attrs["city"] = city

        price_city = attrs.pop("price_city_id", None)
        if price_city and not rop_profile.cities.filter(id=price_city.id).exists():
            raise serializers.ValidationError({"price_city_id": "Данный город не поддерживается или вам не доступен"})

        if price_city:
            attrs["price_city"] = price_city

        dealer_status = attrs.pop("dealer_status_id", None)
        if dealer_status:
            attrs["dealer_status"] = dealer_status

        return attrs


class DealerBalanceHistorySerializer(serializers.ModelSerializer):
    balance_crm = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = BalanceHistory
        fields = ("id", "created_at", "status", "balance_crm", "amount")

    def get_balance_crm(self, instance) -> Decimal:
        match instance.status:
            case "order":
                return instance.balance + instance.amount
            case "wallet":
                return instance.balance - instance.amount


class DealerBasketProductSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField(read_only=True)
    amount = serializers.SerializerMethodField(read_only=True)
    discount = serializers.SerializerMethodField(read_only=True)
    stock_count = serializers.SerializerMethodField(read_only=True)
    stock_city = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CartProduct
        fields = ("id", "product_name", "count", "amount", "discount", "stock_city", "stock_count")
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


# --------------------------------------------------- ORDER
class ShortOrderSerializer(serializers.ModelSerializer):
    dealer_city = serializers.SerializerMethodField(read_only=True)
    stock_city = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MyOrder
        fields = ("id", "name", "dealer_city", "stock_city", "price", "type_status",
                  "created_at", "paid_at", "released_at", "is_active")

    def get_dealer_city(self, instance):
        if instance.author:
            return instance.author.city.title

    def get_stock_city(self, instance):
        if instance.stock:
            return instance.stock.city.title


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
        fifteen_days_ago = timezone.now() - timezone.timedelta(days=15)
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

    class Meta:
        model = Wallet
        fields = ("id", "user_id", "name", "amount_1c", "paid_amount", "amount_crm", "city", "status",
                  "last_replenishment_date")

    def get_name(self, instance):
        return instance.dealer.user.name

    def get_paid_amount(self, instance) -> float:
        return instance.dealer.orders.filter(is_active=True, paid_at__isnull=False).aggregate(
            amount=Round(Sum("price", output_field=FloatField()), precision=2)
        )["amount"]

    def get_city(self, instance):
        return instance.dealer.city.title

    def get_status(self, instance):
        return instance.dealer.dealer_status.title

    def get_last_replenishment_date(self, instance) -> datetime:
        last_replenishment = instance.dealer.balance_histories.filter(status="wallet").last()
        if last_replenishment:
            return last_replenishment.created_at


# --------------------------------------- TASKS
class ShortTaskSerializer(serializers.ModelSerializer):
    provider = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CRMTask
        fields = ("id", "created_at", "title", "end_date", "provider", "status")

    def get_provider(self, obj):
        return obj.creator.name


class RopTaskListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRMTaskResponse
        fields = ("id", "task", "grade", "is_done")

    def get_status(self, obj):
        return obj.task.status


class TaskFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRMTaskFile
        fields = ("file",)


class TaskResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRMTaskResponseFile
        fields = ("file",)


class RopTaskDetailSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField(read_only=True)
    task_text = serializers.SerializerMethodField(read_only=True)
    end_date = serializers.SerializerMethodField(read_only=True)
    task_files = serializers.SerializerMethodField(read_only=True)
    response_files = TaskResponseSerializer(many=True, required=False)

    class Meta:
        model = CRMTaskResponse
        fields = ("id", "title", "task_text", "text", "task_files", "response_files", "end_date", "grade", "is_done")
        read_only_fields = ("grade", "is_done")

    def get_title(self, obj):
        return obj.task.title

    def get_task_text(self, obj):
        return obj.task.text

    def get_end_date(self, obj) -> datetime:
        return obj.task.end_date

    def get_task_files(self, obj) -> TaskFileSerializer:
        return TaskFileSerializer(instance=obj.task.files.all(), many=True).data

    def update(self, instance, validated_data):
        files = [
            CRMTaskResponseFile(task=instance, file=file_data['file'])
            for file_data in validated_data.pop("files", [])
        ]
        with transaction.atomic():
            validated_data['is_done'] = True
            instance = super().update(instance, validated_data)

            if files:
                CRMTaskResponseFile.objects.bulk_create(files)

            task = instance.task
            task.status = "wait"
            task.save()
        return instance
