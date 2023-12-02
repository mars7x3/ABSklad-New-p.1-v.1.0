
from rest_framework import serializers

from .models import *


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

