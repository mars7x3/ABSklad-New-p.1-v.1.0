
from rest_framework import serializers

from .models import *
from product.models import AsiaProduct, ProductImage, ProductPrice


class StoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        fields = ('id', 'file')


class StoryDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        exclude = ('clicks', 'dealer_profiles', 'end_date', 'is_active')

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
        prices = instance.prices.filter(price_type=user.dealer_profile.price_type,
                                        d_status=user.dealer_profile.dealer_status)
        if not prices:
            prices = instance.prices.filter(city=user.dealer_profile.price_city,
                                            d_status=user.dealer_profile.dealer_status)
        rep['price_info'] = StoryProductPriceSerializer(prices.first(), context=self.context).data
        return rep


class StoryProductPriceSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductPrice
        fields = ('price', 'old_price', 'discount', 'discount_status')


class StoryProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('image',)


class MotivationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Motivation
        exclude = ('dealers',)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['conditions'] = MotivationConditionSerializer(instance.conditions, many=True, context=self.context).data

        return rep


class MotivationConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MotivationCondition
        exclude = ('id', 'motivation')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['presents'] = MotivationPresentSerializer(instance.presents, many=True, context=self.context).data

        match instance.status:
            case 'category':
                rep['condition_cats'] = ConditionCategorySerializer(instance.condition_cats, many=True,
                                                                    context=self.context).data
            case 'product':
                rep['condition_prods'] = ConditionProductSerializer(instance.condition_prods, many=True,
                                                                    context=self.context).data

        return rep


class ConditionCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ConditionCategory
        exclude = ('id', 'condition')


class ConditionProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConditionProduct
        exclude = ('id', 'condition')


class MotivationPresentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MotivationPresent
        exclude = ('id', 'condition')


class BannerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        exclude = ('dealer_profiles', 'clicks', 'is_active', 'products', 'web_image', 'discount', 'motivation',
                   'created_at', 'description', 'video_url')


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        exclude = ('dealer_profiles', 'clicks', 'is_active', 'web_image', 'discount', 'motivation', 'created_at')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['products'] = StoryProductSerializer(instance.products.all(),
                                                 many=True, context=self.context).data
        return rep


class DealerKPISerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerKPI
        fields = '__all__'
