
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
        representation = super().to_representation(instance)
        representation['products'] = StoryProductSerializer(instance.products.all(),
                                                            many=True, context=self.context).data
        return representation


class StoryProductSerializer(serializers.ModelSerializer):
    avg_rating = serializers.DecimalField(max_digits=100, decimal_places=2, coerce_to_string=False)

    class Meta:
        model = AsiaProduct
        fields = ('id', 'description', 'avg_rating', 'reviews_count')

    def to_representation(self, instance):
        user = self.context.get('request').user
        representation = super().to_representation(instance)
        representation['images'] = StoryProductImageSerializer(instance.images.first(), context=self.context).data
        representation['price'] = instance.prices.filter(city=user.dealer_profile.price_city,
                                                         d_status=user.dealer_profile.dealer_status).first().price
        return representation


class StoryProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('image',)
