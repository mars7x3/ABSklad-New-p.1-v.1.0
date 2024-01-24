from django.db.models import Sum, IntegerField
from rest_framework import serializers

from one_c.models import MoneyDoc
from order.models import MyOrder, OrderProduct
from .models import StockGroupStat, StockStat


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockStat
        fields = ("id", "title")
        extra_kwargs = {"id": {"source": "stock_id"}}


class StockGroupSerializer(serializers.ModelSerializer):
    stock = StockSerializer(read_only=True, many=False, source="stock_stat")

    class Meta:
        model = StockGroupStat
        exclude = ("id", "stat_type",)


class TransactionSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MoneyDoc
        fields = ("id", "user_name", "status", "amount", "created_at")

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.name


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField(read_only=True)
    price = serializers.SerializerMethodField(read_only=True)
    count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MyOrder
        fields = ("id", "user", "price", "count")

    def get_user(self, obj):
        if obj.author:
            user = obj.author.user
            return {
                "id": user.id,
                "name": user.name
            }

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
