
from rest_framework import serializers

from crm_general.utils import create_product_recommendation
from .models import *
from .tasks import create_avg_rating


class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ('image',)


class ReviewResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewResponse
        fields = ('text', 'created_at')


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ('id', 'rating', 'text', 'created_at', 'product')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        user = instance.author
        if user.image:
            representation['author_image'] = self.context['request'].build_absolute_uri(user.image.url)
        else:
            representation['author_image'] = "Нет фото"
        representation['author_name'] = user.name
        representation['images'] = ReviewImageSerializer(instance.images, many=True, context=self.context).data
        representation['review_response'] = ReviewResponseSerializer(
            instance.review_response, many=True, context=self.context).data

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
        create_avg_rating(review.id)
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
        rep['images'] = ProductImageSerializer([instance.images.first()], many=True, context=self.context).data
        rep['collection'] = instance.collection.title if instance.collection else '---'

        request = self.context['request']
        user = request.user
        dealer = user.dealer_profile

        if request.query_params.get('discount'):
            discount_price = user.discount_prices.select_related('discount').filter(
                is_active=True,
                product=instance,
                price_type=dealer.price_type).first()
            if discount_price:
                rep['price_info'] = {
                    'price': discount_price.price,
                    'old_price': discount_price.old_price,
                    'discount': discount_price.discount.amount,
                    'discount_status': discount_price.discount.status
                }
                return rep

            discount_price = user.discount_prices.select_related('discount').filter(
                is_active=True,
                product=instance,
                city=dealer.price_city).first()
            if discount_price:
                rep['price_info'] = {
                    'price': discount_price.price,
                    'old_price': discount_price.old_price,
                    'discount': discount_price.discount.amount,
                    'discount_status': discount_price.discount.status
                }
                return rep

            rep['price_info'] = {
                'price': 0.0,
                'old_price': 0.0,
                'discount': 0.0,
                'discount_status': "Per"
            }
            return rep

        else:
            prices = instance.prices.filter(price_type=dealer.price_type, d_status=dealer.dealer_status).first()
            if not prices:
                prices = instance.prices.filter(city=dealer.price_city, d_status=dealer.dealer_status).first()

            if prices:
                rep['price_info'] = ProductPriceListSerializer(
                    instance=prices,
                    many=False,
                    context=self.context
                ).data

            else:
                rep['price_info'] = {
                    'price': 0.0,
                    'old_price': 0.0,
                    'discount': 0.0,
                    'discount_status': "Per"
                }

            return rep


class ProductPriceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPrice
        fields = ('price', 'old_price', 'discount', 'discount_status')


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('image', 'position')


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
        rep['images'] = ProductImageSerializer(instance.images, many=True, context=self.context).data
        rep['sizes'] = ProductSizeSerializer(instance.sizes, many=True, context=self.context).data
        rep['counts'] = ProductCountSerializer(instance.counts, many=True, context=self.context).data
        image_list = ReviewImage.objects.filter(review__product=instance, review__is_active=True)
        rep['reviews_images'] = ReviewsImagesSerializer(image_list, many=True, context=self.context).data
        rep['category'] = instance.category.title if instance.category else '---'
        rep['collection'] = instance.collection.title if instance.collection else '---'

        request = self.context['request']
        user = request.user
        dealer = user.dealer_profile

        create_product_recommendation(user=user, product=instance)

        if user.discount_prices.filter(is_active=True, product=instance):
            discount_price = user.discount_prices.select_related('discount').filter(
                is_active=True,
                product=instance,
                price_type=dealer.price_type).first()
            if discount_price:
                rep['price_info'] = {
                    'price': discount_price.price,
                    'old_price': discount_price.old_price,
                    'discount': discount_price.discount.amount,
                    'discount_status': discount_price.discount.status
                }
                return rep

            discount_price = user.discount_prices.select_related('discount').filter(
                is_active=True,
                product=instance,
                city=dealer.price_city).first()
            if discount_price:
                rep['price_info'] = {
                    'price': discount_price.price,
                    'old_price': discount_price.old_price,
                    'discount': discount_price.discount.amount,
                    'discount_status': discount_price.discount.status
                }
                return rep

            rep['price_info'] = {
                'price': 0.0,
                'old_price': 0.0,
                'discount': 0.0,
                'discount_status': "Per"
            }
            return rep

        else:
            prices = instance.prices.filter(price_type=dealer.price_type, d_status=dealer.dealer_status).first()
            if not prices:
                prices = instance.prices.filter(city=dealer.price_city, d_status=dealer.dealer_status).first()

            if prices:
                rep['price_info'] = ProductPriceListSerializer(
                    instance=prices,
                    many=False,
                    context=self.context
                ).data

            else:
                rep['price_info'] = {
                    'price': 0.0,
                    'old_price': 0.0,
                    'discount': 0.0,
                    'discount_status': "Per"
                }

            return rep


class ReviewsImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ('image',)


class ProductLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('title', 'vendor_code', 'category', 'collection', 'made_in', 'guarantee', 'description',
                  'video_link', 'weight', 'package_count', 'diagram', 'diagram_link')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['images'] = ProductImageSerializer(instance.images, many=True, context=self.context).data
        rep['sizes'] = ProductSizeSerializer(instance.sizes, many=True, context=self.context).data
        rep['category'] = instance.category.title if instance.category else '---'
        rep['collection'] = instance.collection.title if instance.collection else '---'
        return rep
