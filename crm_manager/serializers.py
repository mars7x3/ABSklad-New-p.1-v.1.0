from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Sum, Q
from rest_framework import serializers

from account.models import MyUser, DealerProfile, StaffProfile, BalancePlusFile, BalancePlus
from crm_manager.utils import check_product_count, get_product_list, order_total_price, order_cost_price, \
    generate_order_products
from general_service.models import City, Stock
from order.models import MyOrder, OrderReceipt, OrderProduct
from order.tasks import create_order_notification
from product.models import Category, AsiaProduct, ProductImage, ProductPrice, ProductCount, ProductSize


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("slug", "title",)


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(validators=(validate_password,), required=True, write_only=True)

    class Meta:
        model = MyUser
        fields = ("id", "username", "email", "date_joined", "is_active", "pwd", "password")
        read_only_fields = ("id", "pwd", "date_joined", "is_active")


class DealerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, required=True)
    city = CitySerializer(many=False, read_only=True)

    class Meta:
        model = DealerProfile
        fields = ('user', 'name', 'city', 'dealer_status', 'phone', 'liability', 'price_city')

    def validate(self, attrs):
        attrs['city'] = self.context['request'].user.staff_profile.city
        return attrs

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        validated_data['user'] = MyUser.objects.create_user(status="dealer", **user_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data:
            serializer = UserSerializer(instance=instance.user, data=user_data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return super().update(instance, validated_data)


class StaffProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, required=True)
    city = CitySerializer(many=False, read_only=True)

    class Meta:
        model = StaffProfile
        fields = ("user", "name", "city", "phone")

    def validate(self, attrs):
        user = self.context['request'].user
        attrs['city'] = user.staff_profile.city
        attrs['stock'] = user.staff_profile.stock
        return attrs

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        validated_data['user'] = MyUser.objects.create_user(status="warehouse", **user_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data:
            serializer = UserSerializer(instance=instance.user, data=user_data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return super().update(instance, validated_data)


class CategoryInventorySerializer(serializers.ModelSerializer):
    crm_count = serializers.SerializerMethodField(read_only=True)
    orders_count = serializers.SerializerMethodField(read_only=True)
    count_1c = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Category
        fields = ("slug", "title", "is_active", "uid", "image", "crm_count", "orders_count", "count_1c")

    def get_stock_id(self):
        return self.context.get("stock_id", None)

    def get_crm_count(self, instance):
        stock_id = self.get_stock_id()
        return sum(
            instance.products.annotate(
                counts_sum=Sum("counts__count", filter=Q(counts__stock_id=stock_id) if stock_id else None)
            ).values_list('counts_sum', flat=True)
        )

    def get_orders_count(self, instance):
        stock_id = self.get_stock_id()
        return sum(
            instance.products.annotate(
                orders_count=Sum('order_products__count',
                                 filter=Q(
                                     order_products__order__is_active=True,
                                     order_products__order__status="Оплачено",
                                     order_products__order__stock_id=stock_id,
                                 ) if stock_id else None)
            ).values_list("orders_count", flat=True)
        )

    def get_count_1c(self, instance):
        return self.get_crm_count(instance) + self.get_orders_count(instance)


class ProductInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCount
        fields = ("crm_count", "orders_count", "count_1c")


class ShortProductSerializer(serializers.ModelSerializer):
    counts = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AsiaProduct
        fields = ("id", "title", "counts")

    def get_counts(self, instance):
        stock_id = self.context.get("stock_id", None)
        return ProductInventorySerializer(
            instance.counts.filter(stock_id=stock_id) if stock_id else instance.counts.all(),
            many=True,
            context=self.context
        ).data


class ShortCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('slug', 'title')


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "position")


class ProductPriceSerializer(serializers.ModelSerializer):
    city = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = ProductPrice
        fields = ("id", "city", "dealer_status", "price", "old_price", "discount")


class ProductSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSize
        exclude = ("id",)


class ProductSerializer(ShortProductSerializer):
    collection = serializers.SlugRelatedField(slug_field='slug', read_only=True)
    category = ShortCategorySerializer(many=False)
    prices = serializers.SerializerMethodField(read_only=True)
    sizes = ProductSizeSerializer(many=True)
    images = ProductImageSerializer(many=True)

    class Meta:
        model = AsiaProduct
        fields = ("id", "uid", "vendor_code", "title", "description", "is_active", "video_link", "made_in",
                  "guarantee", "weight", "package_count", "avg_rating", "reviews_count", "created_at", "updated_at",
                  "collection", "category",  "counts", "sizes", "images")

    def get_prices(self, instance):
        city = self.context.get('city')
        return ProductPriceSerializer(
            instance=instance.prices.filter(city=city) if city else instance.prices.all(),
            many=True,
            context=self.context
        ).data


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyOrder
        fields = ("id", "dealer", "status", "name", "gmail", "phone", "address", "price", "type_status", "created_at",
                  "paid_at", "released_at")


class OrderReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderReceipt
        fields = ("id", "file", "created_at")


class OrderProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderProduct
        fields = ("id", "ab_product", "category", "title", "count", "price", "total_price", "discount", "image")


class CRMOrderReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderReceipt
        exclude = ('id', 'order')


class CRMOrderProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderProduct
        exclude = ('id', 'order', 'category', 'ab_product', 'discount')


class CRMStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        exclude = ('is_show', 'is_active', 'uid')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['city'] = instance.city.title
        return rep


class MangerOrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyOrder
        exclude = ('cost_price', 'is_active', 'uid', 'updated_at', 'cash_box', 'author')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['receipts'] = CRMOrderReceiptSerializer(instance.order_receipts.all(), many=True, context=self.context).data
        rep['products'] = CRMOrderProductSerializer(instance.order_products.all(), many=True, context=self.context).data
        rep['stock'] = CRMStockSerializer(instance.stock, context=self.context).data

        return rep

    def validate(self, data):
        request = self.context.get('request')
        products = request.data.get('products')
        user_id = request.data.get('user_id')
        user = MyUser.objects.filter(id=user_id).first()
        dealer = user.dealer_profile

        if not check_product_count(products, data['stock']):
            raise serializers.ValidationError({'text': 'Количество товара больше чем есть в наличии!'})

        product_list = get_product_list(products)
        data['price'] = order_total_price(product_list, products, dealer)

        if data['type_status'] == 'Баллы':
            data['status'] = 'Оплачено'
            if data['price'] > dealer.wallet.amount_crm:
                raise serializers.ValidationError({'text': 'У вас недостаточно средств на балансе!'})

        data['author'] = dealer
        data['name'] = dealer.name
        data['gmail'] = user.email
        data['cash_box'] = data['stock'].cash_box
        data['cost_price'] = order_cost_price(product_list, products)
        data['products'] = generate_order_products(product_list, products, dealer)
        return data

    def create(self, validated_data):
        with transaction.atomic():
            products = validated_data.pop('products')

            order = MyOrder.objects.create(**validated_data)
            OrderProduct.objects.bulk_create([OrderProduct(order=order, **i) for i in products])
            create_order_notification(order.id)  # TODO: delay() add here
            return order


class ManagerOrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyOrder
        fields = ('id', 'price', 'created_at', 'status')


class ManagerOrderDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyOrder
        exclude = ('cost_price', 'is_active', 'uid', 'updated_at', 'cash_box', 'author')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['receipts'] = CRMOrderReceiptSerializer(instance.order_receipts.all(), many=True, context=self.context).data
        rep['products'] = CRMOrderProductSerializer(instance.order_products.all(), many=True, context=self.context).data
        rep['stock'] = CRMStockSerializer(instance.stock, context=self.context).data

        return rep


class CRMBalancePlusSerializer(serializers.ModelSerializer):
    class Meta:
        model = BalancePlus
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['files'] = CRMBalancePlusFileSerializer(instance.files.all(), many=True, context=self.context).data
        return rep


class CRMBalancePlusFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BalancePlusFile
        fields = ('file',)
