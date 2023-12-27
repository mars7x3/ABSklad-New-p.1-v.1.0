import datetime

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from order.models import MyOrder, OrderReceipt, OrderProduct
from product.models import AsiaProduct


class StockProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyOrder
        exclude = ('cost_price', 'uid')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['order_receipts'] = OrderReceiptSerializer(instance.order_receipts, many=True, context=self.context).data
        return rep


class OrderReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderReceipt
        exclude = ('order', 'uid')


class OrderProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderProduct
        exclude = ('order', 'cost_price', 'discount')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['prod_info'] = OrderAsiaProductSerializer(instance.ab_product, context=self.context).data
        return rep


class OrderAsiaProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'title')


