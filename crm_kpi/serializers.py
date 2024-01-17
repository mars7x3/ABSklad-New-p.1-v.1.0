from rest_framework import serializers

from account.models import MyUser
from crm_kpi.models import DealerKPI, DealerKPIProduct, ManagerKPITMZInfo, ManagerKPIPDSInfo
from product.models import AsiaProduct


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

        created = DealerKPI.objects.filter(user=user, month=month)
        if created:
            raise serializers.ValidationError({'detail': f'KPI is already created for user id {user.id}\n'
                                                         f'for current month {month}'})

        instance = super().create(validated_data)

        kpi_products_to_create = []

        for product in products:
            product_instance = AsiaProduct.objects.get(id=product['id'])
            kpi_products_to_create.append(
                DealerKPIProduct(
                    kpi=instance,
                    product=product_instance,
                    count=product['count']
                )
            )

        DealerKPIProduct.objects.bulk_create(kpi_products_to_create)
        return instance


class DealerKPIDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerKPI
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['user__name'] = instance.user.name
        rep['user__city'] = instance.user.dealer_profile.village.city.title
        rep['products'] = DealerKPIProductSerializer(instance.kpi_products.all(), many=True).data
        return rep

    def update(self, instance, validated_data):
        if instance.is_confirmed is not False:
            raise serializers.ValidationError({'detail': 'Can not update KPI which is already confirmed'})
        return super().update(instance, validated_data)


class DealerKPIProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerKPIProduct
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['title'] = instance.product.title
        return rep


class DealerKPITMZTotalSerializer(serializers.Serializer):
    user__name = serializers.CharField()
    total_count = serializers.IntegerField()
    total_fact_count = serializers.IntegerField()


class DealerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('id', 'name')


class ProductListKPISerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'title')


class ManagerKPITMZInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerKPITMZInfo
        fields = '__all__'


class ManagerKPIPDSInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerKPIPDSInfo
        fields = '__all__'
