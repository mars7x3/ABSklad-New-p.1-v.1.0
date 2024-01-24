from django.db.models import Sum, IntegerField
from rest_framework import serializers

from account.models import MyUser
from general_service.models import Stock
from one_c.models import MoneyDoc
from order.models import MyOrder, OrderProduct

from .models import StockGroupStat


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ("id", "title")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ("id", "name")


class StockGroupSerializer(serializers.ModelSerializer):
    stock = StockSerializer(read_only=True, many=False)

    class Meta:
        model = StockGroupStat
        exclude = ("id", "stat_type",)


class TransactionSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)

    class Meta:
        model = MoneyDoc
        fields = ("id", "user", "status", "amount", "created_at")


class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    price = serializers.SerializerMethodField(read_only=True)
    count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MyOrder
        fields = ("user", "price", "count")

    @property
    def product_id(self):
        request = self.context["request"]
        return request.query_params.get("product_id")

    def get_price(self, obj):
        if self.product_id:
            product = obj.order_products.filter(ab_product_id=self.product_id).first()
            if not product:
                return 0
            return product.total_price
        return obj.price

    def get_count(self, obj) -> int:
        query = obj.order_products
        if self.product_id:
            query = obj.order_products.filter(ab_product_id=self.product_id)
        return int(
            query.aggregate(
                total_count=Sum("count", default=0, output_field=IntegerField())
            )["total_count"]
        )


class OrderProductSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField(read_only=True)
    count = serializers.IntegerField()
    created_at = serializers.DateTimeField(source="order.created_at")

    class Meta:
        model = OrderProduct
        fields = ("id", "title", "count", "total_price", "price", "created_at")

    def get_title(self, obj):
        if obj.ab_product:
            return obj.ab_product.title
        return obj.title
