from django.db import transaction
from rest_framework import serializers

from account.models import MyUser, WarehouseProfile, ManagerProfile, RopProfile, Wallet, DealerProfile, BalanceHistory
from crm_general.serializers import CRMCitySerializer, CRMStockSerializer, ABStockSerializer
from general_service.models import Stock, City
from order.models import MyOrder
from product.models import AsiaProduct, Collection, Category
from promotion.models import Discount


class StaffCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('id', 'username', 'status', 'phone', 'pwd', 'email', 'is_active', 'date_joined', 'image',
                  'updated_at', 'password')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.status == 'manager':
            rep['profile'] = ManagerProfileSerializer(instance.manager_profile, context=self.context).data
        if instance.status == 'rop':
            rep['profile'] = RopProfileSerializer(instance.rop_profile, context=self.context).data
        if instance.status == 'warehouse':
            rep['profile'] = WarehouseProfileSerializer(instance.warehouse_profile, context=self.context).data
        return rep

    def validate(self, attrs):
        profile_data = self.context['request'].data.get("profile_data", None)
        attrs['profile_data'] = profile_data
        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            profile_data = validated_data.pop('profile_data')
            user = MyUser.objects.create_user(**validated_data)

            if user.status == 'manager':
                ManagerProfile.objects.create(user=user, city_id=profile_data.get('city'))

            elif user.status == 'rop':
                rop_profile = RopProfile.objects.create(user=user)
                city_ids = profile_data.get("cities", [])
                cities = City.objects.filter(id__in=city_ids)
                rop_profile.cities.add(*cities)

            elif user.status == 'warehouse':
                WarehouseProfile.objects.create(user=user, stock_id=profile_data.get('stock'))

            return user

    def update(self, instance, validated_data):
        with transaction.atomic():
            profile_data = validated_data.pop('profile_data')
            for key, value in validated_data.items():
                setattr(instance, key, value)
            instance.pwd = validated_data.get('password')
            instance.set_password(validated_data.get('password'))
            instance.save()

            if instance.status == 'manager':
                manager_profile = instance.manager_profile
                manager_profile.city_id = profile_data.get('city')
                manager_profile.save()

            elif instance.status == 'rop':
                city_ids = profile_data.get("cities", [])
                cities = City.objects.filter(id__in=city_ids)
                rop_profile = instance.rop_profile
                rop_profile.cities.clear()
                rop_profile.cities.add(*cities)
                rop_profile.save()

            elif instance.status == 'warehouse':
                warehouse_profile = instance.manager_profile
                warehouse_profile.stock_id = warehouse_profile.get('stock')
                warehouse_profile.save()

            return instance


class WarehouseProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseProfile
        exclude = ('id', 'user')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['stock'] = ABStockSerializer(instance.stock, context=self.context).data
        return rep


class RopProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RopProfile
        exclude = ('id', 'user')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['cities'] = CRMCitySerializer(instance.cities.all(), many=True, context=self.context).data
        return rep


class ManagerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerProfile
        exclude = ('id', 'user')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['city'] = CRMCitySerializer(instance.city, context=self.context).data
        return rep


class BalanceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ('amount_crm', 'amount_1c')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['dealer_info'] = BalanceDealerSerializer(instance.dealer, context=self.context).data
        return rep


class BalanceHistoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = BalanceHistory
        fields = ('amount', 'balance', 'status', 'action_id', 'created_at')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['dealer_name'] = instance.dealer.user.name
        return rep

class BalanceDealerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        fields = ('dealer_status', 'city')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['status_title'] = instance.dealer_status.title if instance.dealer_status else '---'
        rep['city_title'] = instance.city.title if instance.city else '---'
        rep['name'] = instance.user.name
        rep['user_id'] = instance.user.id
        last_transaction = instance.balance_history.filter(is_active=True, amount__gte=0).last()
        rep['last_repl'] = last_transaction.created_at if last_transaction else '---'

        return rep


class DirectorProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'title', 'is_active', 'collection', 'category', 'is_discount')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['collection_title'] = instance.collection.title if instance.collection else '---'
        rep['category_title'] = instance.category.title if instance.category else '---'
        rep['stocks_count'] = sum(instance.counts.all().values_list('count_crm', flat=True))
        cost_price = instance.cost_prices.filter(is_active=True).first()
        rep['cost_price'] = cost_price.price if cost_price else '---'
        return rep


class DirectorCollectionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['categories_count'] = len(set(instance.products.values_list('category', flat=True)))
        rep['products_count'] = sum(instance.products.values_list('counts__count_crm', flat=True))
        return rep


class CollectionCategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('title', 'is_active', 'id', 'slug')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['products_count'] = sum(instance.products.values_list('counts__count_crm', flat=True))
        return rep


class CollectionCategoryProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'title', 'is_active', 'is_discount', 'vendor_code', 'created_at')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['stocks_count'] = sum(instance.counts.all().values_list('count_crm', flat=True))
        cost_price = instance.cost_prices.filter(is_active=True).first()
        rep['cost_price'] = cost_price.price if cost_price else '---'
        rep['avg_check'] = sum(instance.order_products.filter(order__is_active=True,
                                                              order__status__in=['Отправлено', 'Успешно', 'Оплачено',
                                                                                 'Ожидание']).values_list('total_price',
                                                                                                          flat=True))

        return rep

# class StockCRUDSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Stock
#         exclude = ('uid', 'is_show')
#
#     def to_representation(self, instance):
#         rep = super().to_representation(instance)
#         rep['city'] = instance.city.title if instance.city else 'Нет города'
#         rep['warehouses'] = instance.warehouse_profiles.values_list("user__name", flat=True)
#         rep['prod_amount_crm'] = instance.total_sum
#         rep['prod_count_crm'] = instance.total_count
#
#         return rep
