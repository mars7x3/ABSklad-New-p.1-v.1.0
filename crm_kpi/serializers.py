import datetime

from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from account.models import MyUser
from crm_kpi.models import DealerKPI, DealerKPIProduct
from product.models import AsiaProduct, ProductPrice


class DealerKPISerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerKPI
        fields = '__all__'

    def create(self, validated_data):
        products = self.context['request'].data.get('products')
        user = validated_data['user']
        month = validated_data['month']
        if products is None:
            raise serializers.ValidationError({'detail': 'products are required'})

        created = DealerKPI.objects.filter(user=user, month__month=month.month, month__year=month.year).first()
        if created:
            raise serializers.ValidationError({'detail': f'KPI is already created for user id {user.id}\n'
                                                         f'for current month {month}'})

        instance = super().create(validated_data)

        kpi_products_to_create = []

        for product in products:
            product_instance = AsiaProduct.objects.get(id=product['id'])
            if user.dealer_profile.price_type:
                product_price = ProductPrice.objects.filter(d_status=user.dealer_profile.dealer_status,
                                                            product_id=product['id'],
                                                            price_type=user.dealer_profile.price_type).first()
                price = product_price.price
            else:
                product_price = ProductPrice.objects.filter(d_status=user.dealer_profile.dealer_status,
                                                            product_id=product['id'],
                                                            city=user.dealer_profile.price_city).first()
                price = product_price.price

            kpi_products_to_create.append(
                DealerKPIProduct(
                    kpi=instance,
                    product=product_instance,
                    count=product['count'],
                    sum=product['count'] * price
                )
            )

        DealerKPIProduct.objects.bulk_create(kpi_products_to_create)
        return instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['user__name'] = instance.user.name
        rep['user__city'] = instance.user.dealer_profile.village.city.title if (instance.user.
                                                                                dealer_profile.village) else ''
        rep['pds_percent_completion'] = round((instance.fact_pds / instance.pds) * 100 if instance.pds > 0 else 0)
        sum_count = instance.kpi_products.all().aggregate(Sum('count'))
        fact_sum_count = instance.kpi_products.all().aggregate(Sum('fact_count'))
        if sum_count['count__sum'] is not None and fact_sum_count['fact_count__sum'] is not None:
            rep['tmz_percent_completion'] = round(fact_sum_count['fact_count__sum'] / sum_count['count__sum'] * 100)
        else:
            rep['tmz_percent_completion'] = 0
        return rep


class DealerKPIDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerKPI
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['user__name'] = instance.user.name
        rep['user__city'] = instance.user.dealer_profile.village.city.title if (instance.user.
                                                                                dealer_profile.village) else ''
        rep['pds_percent_completion'] = round((instance.fact_pds / instance.pds) * 100 if instance.pds > 0 else 0)
        sum_count = instance.kpi_products.all().aggregate(Sum('count'))
        fact_sum_count = instance.kpi_products.all().aggregate(Sum('fact_count'))
        if sum_count['count__sum'] is not None and fact_sum_count['fact_count__sum'] is not None:
            rep['tmz_percent_completion'] = round(fact_sum_count['fact_count__sum'] / sum_count['count__sum'] * 100)
        else:
            rep['tmz_percent_completion'] = 0
        rep['products'] = DealerKPIProductSerializer(instance.kpi_products.all(), many=True).data
        return rep

    def update(self, instance, validated_data):
        products = self.context['request'].data.get('products')
        if instance.is_confirmed is not False:
            raise serializers.ValidationError({'detail': 'Can not update KPI which is already confirmed'})

        instance = super().update(instance, validated_data)
        user = instance.user
        for p in products:
            dealer_product = DealerKPIProduct.objects.filter(product_id=p['product'], kpi=instance).first()

            if user.dealer_profile.price_type:
                product_price = ProductPrice.objects.filter(d_status=user.dealer_profile.dealer_status,
                                                            product_id=p['product'],
                                                            price_type=user.dealer_profile.price_type).first()
                price = product_price.price
            else:
                product_price = ProductPrice.objects.filter(d_status=user.dealer_profile.dealer_status,
                                                            product_id=p['product'],
                                                            city=user.dealer_profile.village.city).first()
                price = product_price.price

            if dealer_product:
                dealer_product.count = p['count']
                dealer_product.sum = p['count'] * price
                dealer_product.save()
            else:
                product = AsiaProduct.objects.filter(id=p['product']).first()
                if product is None:
                    raise serializers.ValidationError({'detail': 'Product not found'})
                count = p['count']
                DealerKPIProduct.objects.create(kpi=instance, product=product, count=p['count'], sum=count * price)

        return instance


class DealerKPIProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerKPIProduct
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['title'] = instance.product.title
        dealer_profile = instance.kpi.user.dealer_profile
        price_type = dealer_profile.price_type
        city = dealer_profile.village.city
        dealer_status = dealer_profile.dealer_status
        if price_type:
            rep['price_title'] = price_type.title
            rep['price'] = instance.product.prices.filter(price_type=price_type, d_status=dealer_status).first().price
        else:
            rep['price_title'] = city.title
            rep['price'] = instance.product.prices.filter(city=city, d_status=dealer_status).first().price
        return rep


class DealerKPITMZTotalSerializer(serializers.Serializer):
    user__name = serializers.CharField()
    total_count = serializers.IntegerField()
    total_fact_count = serializers.IntegerField()


class DealerListSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField(read_only=True)
    city_title = serializers.SerializerMethodField(read_only=True)
    has_kpi = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MyUser
        fields = ('id', 'name', 'city_title', 'status', 'has_kpi')

    def get_status(self, instance) -> bool:
        return instance.dealer_profile.wallet.amount_crm >= 50000

    def get_city_title(self, instance):
        return instance.dealer_profile.village.city.title if instance.dealer_profile.village else ''

    def get_has_kpi(self, instance):
        naive_date = timezone.localtime().now()
        current_date = timezone.make_aware(naive_date)
        kpi = DealerKPI.objects.filter(user=instance, month__month=current_date.month,
                                       month__year=current_date.year).first()
        return True if kpi else False


class ProductListKPISerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('vendor_code', 'id', 'title')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        user_id = self.context['request'].query_params.get('user_id')
        if user_id:
            user = MyUser.objects.filter(id=user_id).first()
            if not user:
                raise serializers.ValidationError({'detail': 'User not found'})
            price_type = user.dealer_profile.price_type
            city = user.dealer_profile.village.city
            dealer_status = user.dealer_profile.dealer_status
            if price_type:
                rep['price_title'] = price_type.title
                rep['price'] = instance.prices.filter(price_type=price_type, d_status=dealer_status).first().price
            else:
                rep['price_title'] = user.dealer_profile.village.city.title
                rep['price'] = instance.prices.filter(city=city, d_status=dealer_status).first().price
        rep['collection__title'] = instance.collection.title if instance.collection else None
        rep['category__title'] = instance.category.title if instance.category else None
        return rep
