from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers
from django.db import transaction

from account.utils import send_push_notification
from product.models import ProductCount, ProductPrice
from .models import *
from .tasks import create_order_notification
from .utils import check_product_count, order_total_price, order_cost_price, get_product_list, generate_order_products


class MyOrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyOrder
        fields = ('id', 'price', 'created_at', 'status')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['stock'] = StockSerializer(instance.stock, context=self.context).data

        return rep


class MyOrderDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyOrder
        exclude = ('cost_price', 'is_active', 'uid', 'updated_at', 'author')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['receipts'] = OrderReceiptSerializer(instance.order_receipts.all(), many=True, context=self.context).data
        rep['products'] = OrderProductSerializer(instance.order_products.all(), many=True, context=self.context).data
        rep['stock'] = StockSerializer(instance.stock, context=self.context).data

        return rep


class OrderReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderReceipt
        exclude = ('id', 'order')


class OrderProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderProduct
        exclude = ('id', 'order', 'category', 'ab_product', 'discount', 'cost_price')


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        exclude = ('is_show', 'is_active', 'uid')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['city'] = instance.city.title
        return rep


class MyOrderCreateSerializer(serializers.ModelSerializer):
    products = serializers.DictField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=True,
        allow_empty=False
    )

    class Meta:
        model = MyOrder
        exclude = ('cost_price', 'is_active', 'uid', 'updated_at', 'author')
        read_only_fields = ('name', 'gmail', 'phone', 'address', 'price',   "status", "comment", "released_at",
                            "paid_at", "products")

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['receipts'] = OrderReceiptSerializer(instance.order_receipts.all(), many=True, context=self.context).data
        rep['products'] = OrderProductSerializer(instance.order_products.all(), many=True, context=self.context).data
        rep['stock'] = StockSerializer(instance.stock, context=self.context).data

        return rep

    def validate(self, data):
        request = self.context.get('request')
        products = request.data.pop('products')
        user = request.user
        dealer = user.dealer_profile

        if not check_product_count(products, data['stock']):
            raise serializers.ValidationError({'text': 'Количество товара больше чем есть в наличии!'})

        product_list = get_product_list(products)
        data['price'] = order_total_price(product_list, products, dealer)

        if data['type_status'] == 'wallet':
            data['status'] = 'paid'
            if data['price'] > dealer.wallet.amount_crm:
                raise serializers.ValidationError({'text': 'У вас недостаточно средств на балансе!'})

        data['author'] = dealer
        data['name'] = user.name
        data['gmail'] = user.email
        data['cost_price'] = order_cost_price(product_list, products)
        data['products'] = generate_order_products(product_list, products, dealer)

        return data

    def create(self, validated_data):
        with transaction.atomic():
            products = validated_data.pop('products')

            order = MyOrder.objects.create(**validated_data)
            OrderProduct.objects.bulk_create([OrderProduct(order=order, **i) for i in products])

            create_order_notification(order.id)  # TODO: delay() add here
            kwargs = {
                "users": [order.author.user],
                "title": f"Заказ #{order.id}",
                "text": "Ваш заказ успешно создан.",
                "link_id": f"{order.id}",
                "status": "order"
            }
            send_push_notification(**kwargs)  # TODO: delay() add here
            return order


class CartListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = ('stock',)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['city'] = instance.stock.city.title
        rep['products'] = CartProductSerializer(instance.cart_products.all(), many=True, context=self.context).data
        return rep


class CartProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartProduct
        fields = ('count',)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['product_info'] = CartAsiaProductSerializer(instance.product, context=self.context).data
        return rep


class CartAsiaProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('title', 'collection', 'id')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        dealer = self.context.get('request').user.dealer_profile
        price = instance.prices.filter(d_status=dealer.dealer_status, price_type=dealer.price_type).first()
        if not price:
            price = instance.prices.filter(d_status=dealer.dealer_status, city=dealer.price_city).first()
        rep['image'] = self.context['request'].build_absolute_uri(instance.images.first().image.url)
        rep['price_info'] = CartAsiaProductPriceSerializer(price, context=self.context).data
        rep['counts'] = CartProductCountSerializer(instance.counts.all(), many=True, context=self.context).data
        rep['collection'] = instance.collection.title if instance.collection else '---'

        return rep


class CartAsiaProductPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPrice
        fields = ('price', 'old_price', 'discount', 'discount_status')


class CartProductCountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCount
        fields = ('stock', 'count_crm', 'arrival_time')


class CartCreateProductSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=AsiaProduct.objects.filter(is_active=True),
        write_only=True,
        required=True
    )
    count = serializers.IntegerField()

    def create(self, validated_data):
        raise NotImplementedError("not implemented!")

    def update(self, instance, validated_data):
        raise NotImplementedError("not implemented!")


class CartCreateItemSerializer(serializers.Serializer):
    stock = serializers.PrimaryKeyRelatedField(
        queryset=Stock.objects.filter(is_active=True),
        write_only=True,
        required=True
    )
    products = CartCreateProductSerializer(many=True, required=True, write_only=True)

    def create(self, validated_data):
        raise NotImplementedError("not implemented!")

    def update(self, instance, validated_data):
        raise NotImplementedError("not implemented!")


@extend_schema_serializer(
    examples=[
         OpenApiExample(
            'Success example',
            description='',
            value={
                'text': "Success!"
            },
            response_only=True
        ),
    ]
)
class CartCreateSerializer(serializers.Serializer):
    carts = CartCreateItemSerializer(many=True, write_only=True, required=True)

    def save(self, **kwargs):
        user = self.context['request'].user
        dealer = user.dealer_profile

        for cart_data in self.validated_data['carts']:
            cart, _ = Cart.objects.get_or_create(dealer=dealer, stock=cart_data['stock'])
            cart.cart_products.all().delete()

            cart_product_list = [
                CartProduct(cart=cart, product=product_data['id'], count=product_data['count'])
                for product_data in cart_data['products']
            ]
            CartProduct.objects.bulk_create(cart_product_list)
        return {"text": "Success!"}

    def create(self, validated_data):
        raise NotImplementedError("not implemented!")

    def update(self, instance, validated_data):
        raise NotImplementedError("not implemented!")
