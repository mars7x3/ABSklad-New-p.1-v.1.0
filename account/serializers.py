from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from general_service.models import Stock, StockPhone
from .models import *


class UserLoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        login = attrs[self.username_field]
        user = get_user_model().objects.filter(Q(username=login) | Q(email=login)).first()

        if user:
            attrs[self.username_field] = user.username

        data = super().validate(attrs)
        data['status'] = self.user.status
        data['user'] = self.user.id
        return data


class DealerMeInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ['email', 'pwd', 'name', 'image', 'phone', 'updated_at', 'id']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['profile'] = DealerProfileSerializer(instance.dealer_profile, context=self.context).data
        return representation


class DealerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        exclude = ['user', 'price_city', 'dealer_status', 'liability', 'id']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['city_title'] = instance.city.title
        return representation


class DealerStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerStore
        exclude = ('dealer',)
        extra_kwargs = {"city": {'required': True}}

    def validate(self, data):
        request = self.context.get('request')
        data['dealer'] = request.user.dealer_profile
        return data


class AccountStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        exclude = ['is_active', 'is_show', 'uid', 'city']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['title'] = instance.city.title
        representation['phones'] = AccountStockPhoneSerializer(instance.phones.all(),
                                                               many=True, context=self.context).data
        return representation


class AccountStockPhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockPhone
        fields = ('phone',)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


class BalancePlusSerializer(serializers.ModelSerializer):
    class Meta:
        model = BalancePlus
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['files'] = BalancePlusFileSerializer(instance.files.all(), many=True, context=self.context).data
        return rep


class BalancePlusFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BalancePlusFile
        fields = ('file', )


class BalanceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BalanceHistory
        exclude = ('is_active', 'dealer')


class DealerProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ['email', 'pwd', 'name', 'phone', 'image']

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        pwd = validated_data.get('pwd')
        if pwd:
            instance.pwd = pwd
            instance.set_password(validated_data.get('pwd'))
        instance.save()
        return instance
