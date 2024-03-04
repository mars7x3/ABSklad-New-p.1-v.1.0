
from rest_framework import serializers

from .models import *


class CountStockListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ('id', 'title')


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ('id', 'address', 'schedule')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['city'] = instance.city.title
        rep['phones'] = StockPhoneSerializer(instance.phones.all(), many=True, context=self.context).data
        return rep


class StockPhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockPhone
        fields = ('phone',)


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ('id', 'title', 'slug')


class RequisiteListSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Requisite
        exclude = ('id', 'category', 'is_active')

    def get_image(self, instance):
        if instance.category.logo:
            logo = self.context.get('request').build_absolute_uri(instance.category.logo.url)
            return logo


class RequisiteCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RequisiteCategory
        exclude = ('is_active',)



