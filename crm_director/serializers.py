from django.db import transaction
from rest_framework import serializers

from account.models import StaffProfile, MyUser, DealerProfile
from crm_director.utils import prod_total_amount_crm
from general_service.models import Stock


class StaffCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('id', 'username', 'status', 'pwd', 'email', 'is_active', 'date_joined')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['user'] = StaffProfileSerializer(instance.staff_profile, context=self.context).data
        return rep

    def create(self, validated_data):
        with transaction.atomic():
            profile_data = validated_data.pop('profile_data')
            user = MyUser.objects.create_user(**validated_data)
            StaffProfile.objects.create(user=user, **profile_data)
            return user

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


class StaffProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffProfile
        exclude = ('id',)


class StockCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        exclude = ('uid', 'is_show')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['city'] = instance.city.title if instance.city else 'Нет города'
        rep['warehouses'] = StaffProfileSerializer(StaffProfile.objects.filter(stock=instance), many=True,
                                                   context=self.context).data
        rep['prod_count_1c'] = sum(instance.counts.only('count_1c').values_list('count_1c', flat=True))
        rep['prod_amount_1c'] = prod_total_amount_crm(instance)
        rep['prod_count_crm'] = sum(instance.counts.only('count_crm').values_list('count_crm', flat=True))
        rep['prod_amount_crm'] = prod_total_amount_crm(instance)

        return rep
