from django.db import transaction
from rest_framework import serializers

from account.models import MyUser, WarehouseProfile, ManagerProfile, RopProfile
from crm_general.director.utils import prod_total_amount_crm
from general_service.models import Stock
from order.db_request import query_debugger


class StaffCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('id', 'username', 'status', 'pwd', 'email', 'is_active', 'date_joined')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.status == 'manager':
            rep['profile'] = ManagerProfileSerializer(instance.manager_profile, context=self.context).data
        if instance.status == 'rop':
            rep['profile'] = RopProfileSerializer(instance.rop_profile, context=self.context).data
        if instance.status == 'warehouse':
            rep['profile'] = WarehouseProfileSerializer(instance.warehouse_profile, context=self.context).data
        return rep

    # def create(self, validated_data):
    #     with transaction.atomic():
    #         profile_data = validated_data.pop('profile_data')
    #         user = MyUser.objects.create_user(**validated_data)
    #         StaffProfile.objects.create(user=user, **profile_data)
    #         return user

    def update(self, instance, validated_data):
        with transaction.atomic():
            profile_data = validated_data.pop('profile_data')

            password = validated_data.pop("password", None)
            if password:
                validated_data['pwd'] = password
                instance.set_password(password)
            user = super().update(instance, validated_data)
            super().update(user.staff_profile, profile_data)

            return user


class WarehouseProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = WarehouseProfile
        # fields = ("stock", "")
        exclude = ('id', 'user')


class RopProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RopProfile
        exclude = ('id', 'user')


class ManagerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerProfile
        exclude = ('id', 'user')


class StockCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        exclude = ('uid', 'is_show')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['city'] = instance.city.title if instance.city else 'Нет города'
        rep['warehouses'] = instance.warehouse_profiles.values_list("user__name", flat=True)
        rep['prod_amount_crm'] = instance.total_sum
        rep['prod_count_crm'] = instance.total_count

        return rep
