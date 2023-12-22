from rest_framework import serializers

from order.models import MyOrder


class OrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyOrder
        fields = '__all__'


class OrderDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyOrder
        fields = '__all__'

