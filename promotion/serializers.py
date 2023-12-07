
from rest_framework import serializers

from .models import *
from product.models import AsiaProduct, ProductImage, ProductPrice


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
    class Meta:
        model = AsiaProduct
        fields = ('id', 'description', 'avg_rating', 'reviews_count', 'title')

    def to_representation(self, instance):
        user = self.context.get('request').user
        rep = super().to_representation(instance)
        rep['images'] = StoryProductImageSerializer([instance.images.first()], many=True, context=self.context).data
        rep['price_info'] = StoryProductPriceSerializer(instance.prices.filter(city=user.dealer_profile.price_city,
                                                   d_status=user.dealer_profile.dealer_status).first(),
                                                   context=self.context).data
        return rep


class StoryProductPriceSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductPrice
        fields = ('price', 'old_price', 'discount', 'discount_status')


class StoryProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('image',)


class TargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Target
        exclude = ('dealer', 'id')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['presents'] = TargetPresentSerializer(instance.presents.all(), many=True, context=self.context).data

        return rep


class TargetPresentSerializer(serializers.ModelSerializer):
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

