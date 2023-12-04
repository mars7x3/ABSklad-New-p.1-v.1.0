
from rest_framework import serializers

from .models import *
from product.models import AsiaProduct, ProductImage


class StoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        fields = ('id', 'image')


class StoryDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['products'] = StoryProductSerializer(instance.products.all(),
                                                 many=True, context=self.context).data
        return rep


class StoryProductSerializer(serializers.ModelSerializer):
    avg_rating = serializers.DecimalField(max_digits=100, decimal_places=2, coerce_to_string=False)

    class Meta:
        model = AsiaProduct
        fields = ('id', 'description', 'avg_rating', 'reviews_count')

    def to_representation(self, instance):
        user = self.context.get('request').user
        rep = super().to_representation(instance)
        rep['images'] = StoryProductImageSerializer(instance.images.first(), context=self.context).data
        rep['price'] = instance.prices.filter(city=user.dealer_profile.price_city,
                                              d_status=user.dealer_profile.dealer_status).first().price
        return rep


class StoryProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('image',)


class TargetSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(max_digits=100, decimal_places=2, coerce_to_string=False)
    completed = serializers.DecimalField(max_digits=100, decimal_places=2, coerce_to_string=False)

    class Meta:
        model = Target
        exclude = ('dealer', 'id')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['presents'] = TargetPresentSerializer(instance.presents.all(), many=True, context=self.context).data

        return rep


class TargetPresentSerializer(serializers.ModelSerializer):
    money = serializers.DecimalField(max_digits=100, decimal_places=2, coerce_to_string=False)

    class Meta:
        model = TargetPresent
        exclude = ('id', 'target')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['product'] = TargetPresentProductSerializer(instance.product).data

        return rep


class TargetPresentProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('title',)

