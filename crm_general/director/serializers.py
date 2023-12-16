from django.db import transaction
from rest_framework import serializers

from account.models import MyUser, WarehouseProfile, ManagerProfile, RopProfile, Wallet, DealerProfile
from crm_general.serializers import CRMCitySerializer, CRMStockSerializer, ABStockSerializer
from general_service.models import Stock, City


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


class BalanceDealerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        fields = ('dealer_status', )

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['dealer_status'] = instance.dealer_status.title if instance.dealer_status.title else '---'
        rep['dealer_status'] = instance.user.name

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
