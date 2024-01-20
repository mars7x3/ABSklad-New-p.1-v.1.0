from rest_framework import serializers

from one_c.models import MoneyDoc
from order.models import MyOrder
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
    user_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MyOrder
        fields = ("id", "user_name", "price", "created_at")

    def get_user_name(self, obj):
        if obj.author:
            return obj.author.user.name
