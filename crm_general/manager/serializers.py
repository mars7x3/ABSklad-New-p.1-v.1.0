from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import F, Q, Sum, Count, Value, DecimalField, FloatField
from django.db.models.functions import Round
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from rest_framework import serializers

from account.models import (
    MyUser, DealerProfile, DealerStatus, Wallet, DealerStore, BalanceHistory,
    BalancePlus, BalancePlusFile
)
from crm_general.serializers import CRMStockSerializer, BaseProfileSerializer
from general_service.models import Stock
from general_service.serializers import CitySerializer
from order.models import MyOrder, OrderProduct, OrderReceipt, CartProduct, ReturnOrder, ReturnOrderProduct
from order.tasks import create_order_notification
from product.models import AsiaProduct, ProductPrice, Collection, Category, ProductSize, ProductImage

from .utils import (
    check_to_unavailable_products, order_total_price, calculate_order_cost_price, build_order_products_data
)


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


class OrderReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderReceipt
        exclude = ("id", "order")


class OrderProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderProduct
        exclude = ("id", "order", "category", "ab_product", "discount")


class OrderSerializer(serializers.ModelSerializer):
    stock = CRMStockSerializer(many=False, read_only=True)
    receipts = OrderReceiptSerializer(many=True, read_only=True, source="order_receipts")
    products = OrderProductSerializer(many=True, read_only=True, source="order_products")

    stock_id = serializers.PrimaryKeyRelatedField(
        queryset=Stock.objects.all(),
        write_only=True,
        required=True
    )
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=MyUser.objects.filter(status="dealer"),
        write_only=True,
        required=True
    )
    product_counts = serializers.DictField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=True,
        allow_empty=False
    )
    type_status = serializers.ChoiceField(choices=MyOrder.TYPE_STATUS)

    class Meta:
        model = MyOrder
        fields = ("id", "name", "gmail", "phone", "address", "stock", "price", "status", "type_status", "comment",
                  "created_at", "released_at", "paid_at", "receipts", "products",
                  "stock_id", "user_id", "product_counts")
        read_only_fields = ("id", "name", "gmail", "price", "stock", "status", "created_at",
                            "released_at", "paid_at")

    def validate(self, attrs):
        user = attrs.pop("user_id", None)
        if user:
            dealer = user.dealer_profile
            attrs["author"] = dealer
            attrs["name"] = user.name
            attrs["gmail"] = user.email
        else:
            dealer = self.instance.author

        try:
            wallet = dealer.wallet
        except ObjectDoesNotExist:
            raise serializers.ValidationError({"user_id": "У пользователя нет кошелька"})

        stock = attrs.pop("stock_id", None) or self.instance.stock
        attrs["stock"] = stock
        product_counts = attrs.pop("product_counts", None)
        if product_counts:
            db_product_ids = AsiaProduct.objects.filter(id__in=list(product_counts.keys())).values_list("id", flat=True)

            if db_product_ids.count() != len(product_counts):
                incorrect_ids = set(str(product_id) for product_id in db_product_ids) - set(product_counts)
                raise serializers.ValidationError(
                    {"product_counts": [f"Неправильный идентификатор продукта: {p_id}" for p_id in incorrect_ids]}
                )

            unavailable_products = check_to_unavailable_products(product_counts, stock)
            if unavailable_products:
                raise serializers.ValidationError(
                    {"product_counts": [
                        {
                            un_product["product_id"]: f"В наличии всего {un_product['count_crm']}!"
                        } for un_product in unavailable_products
                    ]}
                )

            attrs["price"] = order_total_price(product_counts, dealer.price_city, dealer.dealer_status)
            attrs["cost_price"] = calculate_order_cost_price(product_counts)
            try:
                attrs["products"] = build_order_products_data(product_counts, dealer.price_city, dealer.dealer_status)
            except ObjectDoesNotExist:
                raise serializers.ValidationError({"detail": "Попробуйте позже!"})

        if attrs.get("type_status", "") == "Баллы":
            attrs["status"] = "Оплачено"

            price = attrs.get("price") or self.instance.price

            if price > wallet.amount_crm:
                raise serializers.ValidationError({"detail": "Недостаточно средств на балансе!"})

        address = attrs.get("address")
        if not address:
            attrs["address"] = dealer.address
        return attrs

    def create(self, validated_data):
        products = validated_data.pop("products")
        with transaction.atomic():
            order = MyOrder.objects.create(**validated_data)
            OrderProduct.objects.bulk_create([OrderProduct(order=order, **i) for i in products])
            create_order_notification(order.id)  # TODO: delay() add here
            return order


# ---------------------------------------------- DEALER
class DealerStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerStatus
        fields = ("id", "title", "discount")
        read_only_fields = ("title", "discount")


class DealerProfileListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField(read_only=True)
    city = CitySerializer(many=False, read_only=True)
    incoming_funds = serializers.SerializerMethodField(read_only=True)
    shipment_amount = serializers.SerializerMethodField(read_only=True)
    last_order_date = serializers.SerializerMethodField(read_only=True)
    balance_amount = serializers.SerializerMethodField(read_only=True)
    dealer_status = DealerStatusSerializer(many=False, read_only=True)

    class Meta:
        model = DealerProfile
        fields = ("id", "name", "incoming_funds", "shipment_amount", "city", "dealer_status", "last_order_date",
                  "balance_amount")
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


class DealerBirthdaySerializer(serializers.ModelSerializer):
    city = CitySerializer(many=False, read_only=True)
    dealer_status = DealerStatusSerializer(many=False, read_only=True)
    name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DealerProfile
        fields = ("id", "name", "birthday", "city", "dealer_status")
        extra_kwargs = {"id": {"source": "user_id", "read_only": True}}

    def get_name(self, instance) -> str:
        return instance.user.name


class ShortWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ("id", "amount_crm", "amount_1c")


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
    dealer_status_id = serializers.PrimaryKeyRelatedField(
        queryset=DealerStatus.objects.all(),
        required=True,
        write_only=True
    )
    stores = DealerStoreSerializer(many=True, source="dealer_stores", read_only=True)
    liability = serializers.IntegerField(required=True)

    class Meta:
        model = DealerProfile
        fields = ("user", "birthday", "city", "dealer_status", "wallet", "stores", "liability", "dealer_status_id")
        read_only_fields = ("city",)
        user_status = "dealer"

    def validate(self, attrs):
        view = self.context["view"]
        manager_profile_city = view.manager_profile.city
        attrs["city"] = manager_profile_city
        attrs["price_city"] = manager_profile_city
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
                  "last_fifteen_days_ratio", "avg_receipt_amount")

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
                        order__status__in=('Отправлено', 'Оплачено', 'Успешно')
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
        fields = ("id", "name", "amount_1c", "paid_amount", "amount_crm", "city", "status",
                  "last_replenishment_date")

    def get_name(self, instance):
        return instance.dealer.user.name

    def get_created_at(self, instance):
        return instance.dealer.balance_history.last().created_at

    def get_paid_amount(self, instance) -> float:
        return instance.dealer.orders.filter(is_active=True, paid_at__isnull=False).aggregate(
            amount=Round(Sum("price", output_field=FloatField()), precision=2)
        )["amount"]

    def get_city(self, instance):
        return instance.dealer.city.title

    def get_status(self, instance):
        return instance.dealer.dealer_status.title

    def get_last_replenishment_date(self, instance) -> datetime:
        last_replenishment = instance.dealer.balance_history.filter(status="wallet").last()
        if last_replenishment:
            return last_replenishment.created_at


# -------------------------------------------------- RETURNS
class ReturnOrderListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField(read_only=True)
    city = serializers.SerializerMethodField(read_only=True)
    phone = serializers.SerializerMethodField(read_only=True)
    price = serializers.SerializerMethodField(read_only=True)
    email = serializers.SerializerMethodField(read_only=True)
    stock_city = serializers.SerializerMethodField(read_only=True)
    moderated = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ReturnOrder
        fields = ("id", "name", "city", "phone", "email", "stock_city", "price", "moderated", "moder_comment")

    def get_name(self, instance) -> str:
        return instance.order.name

    def get_price(self, instance) -> float:
        return instance.return_products.aggregate(price=Sum(F("price") * F("count")))["price"]

    def get_city(self, instance) -> str | None:
        if instance.order.author and instance.order.author.city:
            return instance.order.author.city.title

    def get_phone(self, instance) -> str:
        return instance.order.phone

    def get_email(self, instance) -> str:
        return instance.order.gmail

    def get_stock_city(self, instance) -> str | None:
        if instance.order.stock:
            return instance.order.stock.city.title

    def get_moderated(self, instance) -> bool:
        return instance.status != "Новый"


class OrderStockInfoSerializer(serializers.ModelSerializer):
    city = serializers.SlugRelatedField(slug_field="title", read_only=True)
    warehouse = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Stock
        fields = ("city", "address", "warehouse")

    def get_warehouse(self, instance) -> dict[str, any]:
        warehouse = instance.warehouse_profiles.first()
        return {
            "name": warehouse.user.name if warehouse else "",
            "phone": warehouse.user.phone if warehouse else ""
        }


class OrderReturnOrderSerializer(serializers.ModelSerializer):
    stock = OrderStockInfoSerializer(many=False, read_only=True)

    class Meta:
        model = MyOrder
        fields = ("name", "gmail", "phone", "address", "type_status", "id", "created_at", "stock")


class OrderReturnProductSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField(read_only=True)
    vendor_code = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ReturnOrderProduct
        fields = ("id", "product_name", "vendor_code", "price", "count")

    def get_product_name(self, instance) -> str:
        return instance.product.title

    def get_vendor_code(self, instance) -> str:
        return instance.product.vendor_code


class ReturnOrderDetailSerializer(serializers.ModelSerializer):
    order = OrderReturnOrderSerializer(many=False, read_only=True)
    price = serializers.SerializerMethodField(read_only=True)
    products = OrderReturnProductSerializer(many=True, read_only=True, source="return_products")
    moder_comment = serializers.CharField(write_only=True, required=True)
    status = serializers.ChoiceField(
        choices=[(status, name) for status, name in ReturnOrder.STATUS if name != "Новый"],
        required=True
    )

    class Meta:
        model = ReturnOrder
        fields = ("order", "price", "products", "moder_comment", "status", "created_at")

    def get_price(self, instance) -> float:
        return instance.return_products.aggregate(price=Sum(F("price") * F("count")))["price"]


class BalancePlusSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=MyUser.objects.filter(status="dealer"),
        write_only=True,
        required=True
    )
    amount = serializers.DecimalField(
        max_digits=100,
        decimal_places=2,
        min_value=0.01,
        required=True
    )
    files = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False, use_url=True),
        required=True,
        source='files__file'
    )

    class Meta:
        model = BalancePlus
        fields = ("id", "dealer", "user_id", "amount", "files")

    def validate(self, attrs):
        user = attrs.pop('user_id', None)
        if user:
            attrs['dealer'] = user.dealer_profile
        return attrs

    def create(self, validated_data):
        # TODO: добавить синхронизацию с 1С
        files = validated_data.pop("files")
        balance = super().create(validated_data)
        BalancePlusFile.objects.bulk_create([BalancePlusFile(balance=balance, file=file) for file in files])
        return balance
