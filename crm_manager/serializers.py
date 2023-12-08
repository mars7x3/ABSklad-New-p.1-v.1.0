from django.db import transaction
from django.db.models import Sum, Q
from rest_framework import serializers

from account.models import MyUser, DealerProfile, StaffProfile, BalancePlusFile, BalancePlus, Wallet
from crm_general.serializers import BaseProfileSerializer
from crm_manager.utils import (
    order_total_price, build_order_products_data, calculate_order_cost_price, check_to_unavailable_products
)
from general_service.models import Stock
from general_service.serializers import CitySerializer
from order.models import MyOrder, OrderReceipt, OrderProduct
from order.tasks import create_order_notification
from product.models import Category, AsiaProduct, ProductImage, ProductPrice, ProductCount, ProductSize


class CRMDealerProfileSerializer(BaseProfileSerializer):
    city = CitySerializer(many=False, read_only=True)
    price_city = CitySerializer(many=False, read_only=True)

    class Meta:
        model = DealerProfile
        fields = ('user', 'name', 'city', 'dealer_status', 'phone', 'liability', 'price_city')
        user_status = "dealer"

    def validate(self, attrs):
        attrs['city'] = self.context['request'].user.staff_profile.city
        attrs['price_city'] = self.context['request'].user.staff_profile.city
        return attrs


class CRMWareHouseProfileSerializer(BaseProfileSerializer):
    city = CitySerializer(many=False, read_only=True)

    class Meta:
        model = StaffProfile
        fields = ("user", "name", "city", "phone")
        user_status = "warehouse"

    def validate(self, attrs):
        user = self.context['request'].user
        attrs['city'] = user.staff_profile.city
        attrs['stock'] = user.staff_profile.stock
        return attrs


class CRMCategorySerializer(serializers.ModelSerializer):
    crm_count = serializers.SerializerMethodField(read_only=True)
    orders_count = serializers.SerializerMethodField(read_only=True)
    count_1c = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Category
        fields = ("slug", "title", "is_active", "uid", "image", "crm_count", "orders_count", "count_1c")

    def get_stock(self):
        return self.context.get("stock", None)

    def get_crm_count(self, instance) -> int:
        stock = self.get_stock()
        return sum(
            instance.products.annotate(
                counts_sum=Sum("counts__count", filter=Q(counts__stock_id=stock.id) if stock else None)
            ).values_list('counts_sum', flat=True)
        )

    def get_orders_count(self, instance) -> int:
        stock = self.get_stock()
        return sum(
            instance.products.annotate(
                orders_count=Sum('order_products__count',
                                 filter=Q(
                                     order_products__order__is_active=True,
                                     order_products__order__status="Оплачено",
                                     order_products__order__stock_id=stock.id,
                                 ) if stock else None)
            ).values_list("orders_count", flat=True)
        )

    def get_count_1c(self, instance) -> int:
        return self.get_crm_count(instance) + self.get_orders_count(instance)


class CRMProductCountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCount
        fields = ("crm_count", "orders_count", "count_1c")


class CRMShortProductSerializer(serializers.ModelSerializer):
    counts = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AsiaProduct
        fields = ("id", "title", "counts")

    def get_counts(self, instance) -> dict[str, int]:
        stock_id = self.context.get("stock_id", None)
        return CRMProductCountSerializer(
            instance.counts.filter(stock_id=stock_id) if stock_id else instance.counts.all(),
            many=True,
            context=self.context
        ).data


class CRMShortCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('slug', 'title')


class CRMProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "position")


class CRMProductPriceSerializer(serializers.ModelSerializer):
    city = CitySerializer(many=False, read_only=True)

    class Meta:
        model = ProductPrice
        fields = ("id", "city", "dealer_status", "price", "old_price", "discount")


class CRMProductSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSize
        exclude = ("id",)


class CRMProductSerializer(CRMShortProductSerializer):
    collection = serializers.SlugRelatedField(slug_field='slug', read_only=True)
    category = CRMShortCategorySerializer(many=False)
    prices = serializers.SerializerMethodField(read_only=True)
    sizes = CRMProductSizeSerializer(many=True)
    images = CRMProductImageSerializer(many=True)

    class Meta:
        model = AsiaProduct
        fields = ("id", "uid", "vendor_code", "title", "description", "is_active", "video_link", "made_in",
                  "guarantee", "weight", "package_count", "avg_rating", "reviews_count", "created_at", "updated_at",
                  "collection", "category",  "counts", "sizes", "images", "prices")

    def get_prices(self, instance) -> list[CRMProductPriceSerializer]:
        city = self.context.get('city')
        return CRMProductPriceSerializer(
            instance=instance.prices.filter(city=city) if city else instance.prices.all(),
            many=True,
            context=self.context
        ).data


class CRMOrderReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderReceipt
        exclude = ('id', 'order')


class CRMOrderProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderProduct
        exclude = ('id', 'order', 'category', 'ab_product', 'discount')


class CRMStockSerializer(serializers.ModelSerializer):
    city = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Stock
        exclude = ('is_show', 'is_active', 'uid')

    def get_city(self, instance):
        return instance.city.title


class ManagerOrderSerializer(serializers.ModelSerializer):
    stock = CRMStockSerializer(many=False, read_only=True)
    receipts = CRMOrderReceiptSerializer(many=True, read_only=True)
    products = CRMOrderProductSerializer(many=True, read_only=True)

    stock_id = serializers.PrimaryKeyRelatedField(
        queryset=Stock.objects.all(),
        write_only=True,
        required=True
    )
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=MyUser.objects.all(),
        write_only=True,
        required=True
    )
    product_counts = serializers.DictField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=True,
        allow_empty=False
    )
    type_status = serializers.ChoiceField(choices=MyOrder.STATUS)

    class Meta:
        model = MyOrder
        fields = ("id", "name", "gmail", "phone", "address", "stock", "price", "status", "type_status", "comment",
                  "created_at", "released_at", "paid_at", "receipts", "products",
                  "stock_id", "user_id", "product_counts")
        read_only_fields = ("id", "name", "gmail", "price", "stock", "address", "status", "created_at",
                            "released_at", "paid_at")

    def validate(self, attrs):
        user = attrs.pop("user_id", None)
        if user:
            dealer = user.dealer_profile
            attrs['author'] = dealer
            attrs['name'] = dealer.name
            attrs['gmail'] = user.email
        else:
            dealer = self.instance.author

        stock = attrs.pop("stock_id", None) or self.instance.stock
        attrs['stock'] = stock
        product_counts = attrs.pop('product_counts', None)
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

            attrs['price'] = order_total_price(product_counts, dealer.price_city, dealer.dealer_status)
            attrs['cost_price'] = calculate_order_cost_price(product_counts)
            attrs['products'] = build_order_products_data(product_counts, dealer.price_city, dealer.dealer_status)

        if attrs.get("type_status", "") == 'Баллы':
            attrs['status'] = 'Оплачено'

            price = attrs.get("price") or self.instance.price
            if price > dealer.wallet.amount_crm:
                raise serializers.ValidationError({'detail': 'Недостаточно средств на балансе!'})
        return attrs

    def create(self, validated_data):
        products = validated_data.pop('products')

        with transaction.atomic():
            order = MyOrder.objects.create(**validated_data)
            OrderProduct.objects.bulk_create([OrderProduct(order=order, **i) for i in products])
            create_order_notification(order.id)  # TODO: delay() add here
            return order


class ManagerShortOrderSerializer(serializers.ModelSerializer):
    stock = CRMStockSerializer(many=False)

    class Meta:
        model = MyOrder
        fields = ('id', 'name', 'stock', 'price', 'status', "created_at", "paid_at", "released_at")


class CRMBalancePlusFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BalancePlusFile
        fields = ('file',)


class CRMBalancePlusSerializer(serializers.ModelSerializer):
    files = CRMBalancePlusFileSerializer(many=True, read_only=True)

    class Meta:
        model = BalancePlus
        fields = "__all__"


class CRMBalancePlusCreateSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=MyUser.objects.all(),
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


class CRMWalletSerializer(serializers.ModelSerializer):
    user = CRMDealerProfileSerializer(many=False, read_only=True)
    amount_paid = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Wallet
        fields = ("id", "user", "amount_crm", "amount_1c", "amount_paid")

    @property
    def _readable_fields(self):
        if self.context.get('only_amounts'):
            return ["amount_crm", "amount_1c", "amount_paid"]
        return super()._readable_fields

    def get_amount_paid(self, instance):
        return MyOrder.objects.filter(status="Оплачено", author=instance.user).aggregate(amount=Sum('price'))['amount']


class CRMWalletAmountSerializer(serializers.Serializer):
    total_one_c = serializers.DecimalField(max_digits=100, decimal_places=2)
    total_crm = serializers.DecimalField(max_digits=100, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=100, decimal_places=2)
