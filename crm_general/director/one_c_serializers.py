from django.utils import timezone
from rest_framework import serializers

from crm_kpi.models import DealerKPI
from general_service.models import Stock, PriceType, City
from product.models import AsiaProduct, ProductPrice
from promotion.models import Discount


class CountProductSerializer(serializers.Serializer):
    stock_id = serializers.IntegerField(write_only=True, required=True)
    count_norm = serializers.IntegerField(write_only=True, required=True)

    def validate(self, attrs):
        if not Stock.objects.filter(id=attrs["stock_id"]).exists():
            raise serializers.ValidationError({"stock_id": "Не найден"})
        return attrs


class ProductTypePriceSerializer(serializers.Serializer):
    id = serializers.IntegerField(write_only=True, required=True)
    price_type = serializers.IntegerField(write_only=True, required=True)
    price = serializers.DecimalField(max_digits=100, decimal_places=2, write_only=True, required=True)

    def validate(self, attrs):
        if not ProductPrice.objects.filter(id=attrs["id"]).exists():
            raise serializers.ValidationError({"id": "Не найден"})

        if not PriceType.objects.filter(id=attrs["price_type"]):
            raise serializers.ValidationError({"price_type": "Не найден"})

        return attrs


class ProductCityPriceSerializer(serializers.Serializer):
    id = serializers.IntegerField(write_only=True, required=True)
    city = serializers.IntegerField(write_only=True, required=True)
    price = serializers.DecimalField(max_digits=100, decimal_places=2, write_only=True, required=True)

    def validate(self, attrs):
        if not ProductPrice.objects.filter(id=attrs["id"]).exists():
            raise serializers.ValidationError({"id": "Не найден"})

        if not City.objects.filter(id=attrs["city"]):
            raise serializers.ValidationError({"city": "Не найден"})

        return attrs


class ValidateProductSerializer(serializers.ModelSerializer):
    cost_price = serializers.DecimalField(max_digits=100, decimal_places=2, write_only=True, required=False)
    stocks = CountProductSerializer(many=True, required=False, write_only=True)
    type_prices = ProductTypePriceSerializer(many=True, required=False, write_only=True)
    city_prices = ProductCityPriceSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = AsiaProduct
        fields = '__all__'

    def validate(self, attrs):
        if self.instance and attrs.get("is_active", True) is False:
            if Discount.objects.filter(is_active=True, products__id=self.instance.id).exists():
                raise serializers.ValidationError(
                    'Невозможно деактивировать продукт который находится в активной акции'
                )

            aware_date = timezone.make_aware(timezone.localtime().now())

            if DealerKPI.objects.filter(
                is_confirmed=True,
                kpi_products__product_id=self.instance.id,
                month__month=aware_date.month,
                month__year=aware_date.year
            ).exists():
                raise serializers.ValidationError(
                    'Невозможно деактивировать продукт который находится в активном KPI'
                )

        if self.instance and (attrs.get("type_prices") or attrs.get("city_prices")) and self.instance.is_discount:
            raise serializers.ValidationError(
                'Невозможно изменить цену на товар со скидкой'
            )
        return attrs

    def update(self, instance, validated_data):
        raise NotImplemented()

    def create(self, validated_data):
        raise NotImplemented()
