from datetime import datetime
from decimal import Decimal

from django.db.models import Sum, Count, FloatField
from django.db.models.functions import Round
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from account.models import (
    MyUser, DealerProfile, DealerStatus, Wallet, DealerStore,
    BalancePlus, BalancePlusFile
)
from crm_general.models import CRMTask
from crm_general.serializers import CRMStockSerializer, BaseProfileSerializer, VillageSerializer
from general_service.models import Stock, PriceType, City
from general_service.serializers import CitySerializer
from order.models import MyOrder, OrderProduct, OrderReceipt, CartProduct, MainOrder, MainOrderProduct, MainOrderReceipt
from order.tasks import create_order_notification
from product.models import AsiaProduct, ProductPrice, Collection, Category, ProductSize, ProductImage, ProductCount

from .utils import (
    check_to_unavailable_products, order_total_price, build_order_products_data,
    update_main_order_product_count, mngr_get_product_price
)


# --------------------------------------------------- ORDER
class MainShortOrderSerializer(serializers.ModelSerializer):
    dealer_city = serializers.SerializerMethodField(read_only=True)
    stock_city = serializers.SerializerMethodField(read_only=True)
    stock_name = serializers.SerializerMethodField(read_only=True)
    stock_address = serializers.SerializerMethodField(read_only=True)
    name = serializers.SerializerMethodField(read_only=True)
    creator_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MyOrder
        fields = ("id", 'name', "dealer_city", "stock_city", "price", "type_status",
                  "created_at", "paid_at", "released_at", "is_active", "status", "stock_name", "stock_address",
                  "creator_name")

    def get_name(self, instance):
        if instance.author:
            return instance.author.user.name

    def get_dealer_city(self, instance):
        if instance.author:
            return instance.author.village.city.title

    def get_stock_city(self, instance):
        if instance.stock:
            return instance.stock.city.title

    def get_stock_name(self, instance):
        if instance.stock:
            return instance.stock.title

    def get_stock_address(self, instance):
        if instance.stock:
            return instance.stock.address

    def get_creator_name(self, instance):
        if instance.creator:
            return instance.creator.name


class OrderReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderReceipt
        exclude = ("id", "order")


class MainOrderReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = MainOrderReceipt
        exclude = ('order',)


class OrderAsiaProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'title', 'category')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['category_title'] = instance.category.title if instance.category else None
        return rep


class OrderProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderProduct
        exclude = ("id", "order", "category", "ab_product", "discount")

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['prod_info'] = OrderAsiaProductSerializer(instance.ab_product, context=self.context).data
        rep['released_at'] = instance.order.released_at if instance.order.released_at else '---'
        return rep


class MainOrderProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = MainOrderProduct
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['prod_info'] = OrderAsiaProductSerializer(instance.ab_product, context=self.context).data
        return rep


class OrderDetailSerializer(serializers.ModelSerializer):
    order_products = OrderProductSerializer(read_only=True, many=True)

    class Meta:
        model = MyOrder
        fields = ('id', 'order_products', 'type_status', 'created_at', 'updated_at', 'paid_at', 'released_at', 'price',
                  'type_status', 'status')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['name'] = instance.author.user.name
        rep['receipts'] = OrderReceiptSerializer(instance.order_receipts, many=True, context=self.context).data
        return rep


class MainOrderSerializer(serializers.ModelSerializer):
    stock = CRMStockSerializer(many=False, read_only=True)
    receipts = OrderReceiptSerializer(many=True, read_only=True)
    products = MainOrderProductSerializer(many=True, read_only=True)
    orders = OrderDetailSerializer(many=True, read_only=True)
    name = serializers.SerializerMethodField(read_only=True)
    customer_id = serializers.SerializerMethodField(read_only=True)
    creator_name = serializers.SerializerMethodField(read_only=True)

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
        model = MainOrder
        fields = ("id", "stock", "price", "status", "type_status",
                  "created_at", "paid_at", "receipts", "products",
                  "stock_id", "user_id", "product_counts", 'name', 'creator_name',
                  'orders', 'customer_id')
        read_only_fields = ("id", "stock", "status", "created_at",
                            "paid_at", 'name')

    def get_name(self, instance):
        if instance.author:
            return instance.author.user.name

    def get_customer_id(self, instance):
        if instance.author:
            return instance.author.user.id

    def get_creator_name(self, instance):
        if instance.creator:
            return instance.creator.name

    def validate(self, attrs):
        creator = self.context['request'].user
        user = attrs.pop("user_id", None)
        if creator:
            attrs['creator'] = creator

        if user:
            dealer = user.dealer_profile
            attrs["author"] = dealer
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

            price_type = dealer.price_type or None
            attrs["price"] = order_total_price(
                product_counts=product_counts,
                dealer_status=dealer.dealer_status,
                city=dealer.village.city,
                price_type=price_type,
            )
            # attrs["cost_price"] = calculate_order_cost_price(product_counts)
            try:
                attrs["products"] = build_order_products_data(
                    product_counts=product_counts,
                    dealer_status=dealer.dealer_status,
                    city=dealer.village.city,
                    price_type=price_type
                )
            except ObjectDoesNotExist:
                raise serializers.ValidationError({"detail": "Попробуйте позже!"})

        if attrs.get("type_status", "") == "wallet":
            attrs["status"] = "paid"

            price = attrs.get("price") or self.instance.price

            if price > wallet.amount_crm:
                raise serializers.ValidationError({"detail": "Недостаточно средств на балансе!"})

        return attrs

    def create(self, validated_data):
        products = validated_data.pop("products")
        main_order = MainOrder.objects.create(**validated_data)
        MainOrderProduct.objects.bulk_create([MainOrderProduct(order=main_order, **i) for i in products])
        create_order_notification(main_order.id)  # TODO: delay() add here
        return main_order


class MainOrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MainOrder
        fields = '__all__'

    def validate(self, attrs):
        request = self.context.get('request')
        main_order_id = self.context['view'].kwargs.get('pk')
        product_counts = request.data.pop('product_counts')
        main_order = MainOrder.objects.get(id=main_order_id)
        dealer = self.instance.author

        if main_order.status != 'created':
            raise serializers.ValidationError(detail={'Заказ можно менять только если он новый'}, code=404)

        attrs['product_counts'] = product_counts
        stock = attrs.get('stock', None)
        if stock is None:
            raise serializers.ValidationError({'detail': 'stock '})

        try:
            wallet = dealer.wallet
        except ObjectDoesNotExist:
            raise serializers.ValidationError({"user_id": "У пользователя нет кошелька"})

        if product_counts:
            unavailable_products = check_to_unavailable_products(product_counts, stock)
            if unavailable_products:
                raise serializers.ValidationError(
                    {"product_counts": [
                        {
                            un_product["product_id"]: f"В наличии всего {un_product['count_crm']}!"
                        } for un_product in unavailable_products
                    ]}
                )

        if attrs.get("type_status", "") == "wallet":
            attrs["status"] = "paid"
            price = attrs.get("price") or self.instance.price

            if price > wallet.amount_crm:
                raise serializers.ValidationError({"detail": "Недостаточно средств на балансе!"})

        return attrs

    def update(self, instance, validated_data):
        product_counts = validated_data.pop('product_counts')
        update_main_order_product_count(main_order=instance, product_counts=product_counts)
        return super().update(instance, validated_data)


# ---------------------------------------------- DEALER
class DealerStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerStatus
        fields = ("id", "title", "discount")
        read_only_fields = ("title", "discount")


class DealerProfileListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField(read_only=True)
    # incoming_funds = serializers.SerializerMethodField(read_only=True)
    # shipment_amount = serializers.SerializerMethodField(read_only=True)
    # last_order_date = serializers.SerializerMethodField(read_only=True)
    balance_amount = serializers.SerializerMethodField(read_only=True)
    dealer_status = DealerStatusSerializer(many=False, read_only=True)
    # status = serializers.SerializerMethodField(read_only=True)
    is_active = serializers.SerializerMethodField(read_only=True)
    village = serializers.SerializerMethodField(read_only=True)
    city = serializers.SerializerMethodField(read_only=True)

    # motivations = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DealerProfile
        fields = ("id", 'name', "village", "dealer_status", "balance_amount", "is_active", 'city')
        extra_kwargs = {"id": {"source": "user_id", "read_only": True}}

    def get_name(self, instance):
        return instance.user.name

    def get_city(self, instance):
        return instance.village.city.title if instance.village else None

    def get_village(self, instance):
        return instance.village.title if instance.village else None

    def get_balance_amount(self, instance) -> Decimal:
        try:
            return instance.wallet.amount_crm
        except ObjectDoesNotExist:
            return 0.0

    # def get_last_order_date(self, instance) -> date | None:
    #     last_order = instance.orders.only("created_at").order_by("-created_at").first()
    #     if last_order:
    #         return last_order.created_at.date()
    #
    # def get_status(self, instance) -> bool:
    #     return instance.wallet.amount_crm > 50000

    def get_is_active(self, instance) -> bool:
        return instance.user.is_active
    #
    # def get_motivations(self, instance):
    #     return get_motivation_done(instance)


class DealerBirthdaySerializer(serializers.ModelSerializer):
    village = VillageSerializer(many=False, read_only=True)
    dealer_status = DealerStatusSerializer(many=False, read_only=True)
    name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DealerProfile
        fields = ("id", "name", "birthday", "village", "dealer_status")
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


class PriceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceType
        fields = "__all__"


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
    price_type = PriceTypeSerializer(many=False, read_only=True)
    price_type_id = serializers.PrimaryKeyRelatedField(
        queryset=PriceType.objects.all(),
        required=False
    )
    price_city = CitySerializer(many=False, read_only=True)
    price_city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        required=False
    )

    class Meta:
        model = DealerProfile
        fields = ("user", "address", "birthday", "village", "dealer_status", "wallet", "stores",
                  "liability", "dealer_status_id", "price_type", "price_type_id", "motivations", 'price_city',
                  'price_city_id')
        user_status = "dealer"
        read_only_fields = ("motivations",)

    def validate(self, attrs):
        attrs['managers'] = [self.context['request'].user.id]

        village = attrs.pop("village", None)
        if village:
            attrs["village_id"] = village.id
            attrs["price_city_id"] = village.city.id

        price_type = attrs.pop("price_type_id", None)
        if price_type:
            attrs["price_type_id"] = price_type.id

        dealer_status = attrs.pop("dealer_status_id", None)
        if dealer_status:
            attrs["dealer_status_id"] = dealer_status.id
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

    def get_stock_name(self, instance):
        return instance.cart.stock.title

    def get_stock_address(self, instance):
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
    # avg_receipt_amount = serializers.SerializerMethodField(read_only=True)
    # last_fifteen_days_ratio = serializers.SerializerMethodField(read_only=True)
    price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AsiaProduct
        fields = ("id", "title", "vendor_code", "collection", "category", "is_discount", "is_active",
                  "created_at", 'price', 'diagram_link')

    def get_collection(self, instance):
        return instance.collection.title if instance.collection else None

    def get_category(self, instance):
        return instance.category.title if instance.category else None

    # def get_last_fifteen_days_ratio(self, instance):
    #     fifteen_days_ago = timezone.now() - timezone.timedelta(days=15)
    #     return instance.order_products.aggregate(
    #         last_fifteen_days_ratio=Round(
    #             Sum(
    #                 "count",
    #                 filter=Q(
    #                     order__is_active=True,
    #                     order__created_at__gte=fifteen_days_ago,
    #                     order__status__in=("paid", "success", "sent")
    #                 ),
    #                 output_field=FloatField()
    #             ) / Value(15),
    #             precision=2
    #         )
    #     )["last_fifteen_days_ratio"]
    #
    # def get_avg_receipt_amount(self, instance):
    #     return instance.order_products.aggregate(
    #         avg_receipt_amount=Sum("total_price") / Sum("count")
    #     )["avg_receipt_amount"]

    def get_price(self, instance):
        user = self.context['request'].user
        price = instance.prices.filter(city=user.manager_profile.city, d_status__discount=0).first()
        if price:
            return price.price
        return price


class ProductPriceListSerializer(serializers.ModelSerializer):
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
    price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AsiaProduct
        fields = ("id", "images", "diagram", "title", "vendor_code", "description", "sizes", "collection",
                  "weight", "package_count", "made_in", "created_at", "updated_at", 'price')

    def get_price(self, instance):
        user = self.context['request'].user
        price = instance.prices.filter(city=user.manager_profile.city, d_status__discount=0).first()
        if price:
            return price.price
        return price


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

    def get_user_id(self, obj):
        return obj.dealer.user.id

    def get_name(self, instance):
        return instance.dealer.user.name

    def get_created_at(self, instance):
        money_docs = instance.dealer.user.money_docs.filter(is_active=True)
        return money_docs.last().created_at if money_docs else None

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
        return last_replenishment.created_at if last_replenishment else None


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
        required=False,
        source="files__file"
    )

    class Meta:
        model = BalancePlus
        fields = ("id", "dealer", "user_id", "amount", "files")
        read_only_fields = ("dealer",)

    def validate(self, attrs):
        user = attrs.pop('user_id', None)
        if user:
            attrs['dealer'] = user.dealer_profile
        return attrs

    def create(self, validated_data):
        # TODO: добавить синхронизацию с 1С
        files = validated_data.pop("files__file", None)
        balance = super().create(validated_data)
        BalancePlusFile.objects.bulk_create([BalancePlusFile(balance=balance, file=file) for file in files])
        return balance


# --------------------------------------- TASKS
class ShortTaskSerializer(serializers.ModelSerializer):
    provider = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CRMTask
        fields = ("id", "created_at", "title", "end_date", "provider", "status")

    def get_provider(self, obj):
        return obj.creator.name


class ProductListForOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ("id", "title")

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        user_id = self.context.get('request').query_params.get('user_id')
        user = MyUser.objects.get(id=user_id)

        rep['price'] = mngr_get_product_price(user, instance)
        rep['count'] = ProductCountForOrderSerializer(instance.counts, many=True, context=self.context).data

        return rep


class ProductCountForOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCount
        fields = ("stock", "count_crm")

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['stock_title'] = instance.stock.title
        return rep
