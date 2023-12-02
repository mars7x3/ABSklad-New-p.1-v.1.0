
from rest_framework import serializers
from django.db import transaction

from product.models import ProductCount
from .models import *
from .tasks import create_order_notification
from .utils import check_product_count, order_total_price, order_cost_price, get_product_list, generate_order_products


class MyOrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyOrder
        fields = ('id', 'price', 'created_at', 'status')


class MyOrderDetailSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=100, decimal_places=2, coerce_to_string=False, required=False)

    class Meta:
        model = MyOrder
        exclude = ('cost_price', 'is_active', 'uid', 'updated_at', 'cash_box', 'author')

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
        exclude = ('id', 'order', 'category', 'ab_product', 'discount')


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        exclude = ('is_show', 'is_active', 'uid')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['city'] = instance.city.title
        return rep


class MyOrderCreateSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=100, decimal_places=2, coerce_to_string=False, required=False)

    class Meta:
        model = MyOrder
        exclude = ('cost_price', 'is_active', 'uid', 'updated_at', 'cash_box', 'author')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['receipts'] = OrderReceiptSerializer(instance.order_receipts.all(), many=True, context=self.context).data
        rep['products'] = OrderProductSerializer(instance.order_products.all(), many=True, context=self.context).data
        rep['stock'] = StockSerializer(instance.stock, context=self.context).data

        return rep

    def validate(self, data):
        request = self.context.get('request')
        products = request.data.get('products')
        user = request.user
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
        fields = ('product', 'count')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['product_info'] = CartAsiaProductSerializer(instance.product, context=self.context).data
        return rep


class CartAsiaProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('title', 'collection')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        dealer = self.context.get('request').user.dealer_profile
        price = instance.prices.filter(d_status=dealer.dealer_status, city=dealer.price_city).first()
        rep['image'] = self.context['request'].build_absolute_uri(instance.images.first().image.url)
        rep['price'] = price.price
        rep['old_price'] = price.old_price
        rep['counts'] = CartProductCountSerializer(instance.counts.all(), many=True, context=self.context).data

        return rep


class CartProductCountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCount
        fields = ('stock', 'count_crm', 'arrival_time')
