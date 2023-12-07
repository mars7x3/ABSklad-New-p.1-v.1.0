
from rest_framework import serializers

from .models import *
from .tasks import create_avg_rating


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ('id', 'rating', 'text', 'created_at', 'product')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        author_profile = instance.author.dealer_profile
        if author_profile.image:
            representation['author_image'] = self.context['request'].build_absolute_uri(author_profile.image.url)
        representation['author_name'] = author_profile.name

        return representation

    def validate(self, data):
        request = self.context.get('request')
        data['author'] = request.user
        data['images'] = request.FILES.getlist('images')

        return data

    def create(self, validated_data):
        images = validated_data.pop('images')
        review = Review.objects.create(**validated_data)
        ReviewImage.objects.bulk_create([ReviewImage(review=review,  image=i) for i in images])
        create_avg_rating.delay(review.id)
        return review


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('title', 'slug', 'image')


class CollectionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = '__all__'


class ProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'title', 'collection', 'avg_rating', 'reviews_count', 'description')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        dealer = self.context.get('request').user.dealer_profile
        rep['price_info'] = ProductPriceListSerializer(
            instance=instance.prices.filter(city=dealer.price_city, d_status=dealer.dealer_status).first(),
            many=False,
            context=self.context
        ).data
        rep['images'] = ProductImageSerializer([instance.images.first()], many=True, context=self.context).data
        if instance.collection:
            rep['collection'] = instance.collection.title

        return rep


class ProductPriceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPrice
        fields = ('price', 'old_price', 'discount', 'discount_status')


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('image',)


class ProductSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSize
        exclude = ('product', 'id')


class ProductCountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCount
        fields = ('stock', 'count_crm', 'arrival_time')


class ProductDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        exclude = ('is_active', 'is_show', 'is_hit', 'uid', 'created_at', 'updated_at', 'collection')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        dealer = self.context.get('request').user.dealer_profile
        rep['images'] = ProductImageSerializer([instance.images.first()], many=True, context=self.context).data
        rep['sizes'] = ProductSizeSerializer(instance.sizes, many=True, context=self.context).data
        rep['counts'] = ProductCountSerializer(instance.counts, many=True, context=self.context).data

        rep['price_info'] = ProductPriceListSerializer(instance.prices.filter(city=dealer.price_city,
                                                                              d_status=dealer.dealer_status).first(),
                                                       context=self.context).data
        if instance.category:
            rep['category'] = instance.category.title
        return rep



