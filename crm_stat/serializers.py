from rest_framework import serializers

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
