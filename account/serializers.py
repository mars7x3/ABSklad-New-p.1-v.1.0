import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import ASCIIUsernameValidator
from general_service.models import Stock, StockPhone
from .models import *
from .utils import username_is_valid, pwd_is_valid


class UserLoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        login = attrs[self.username_field]
        user = get_user_model().objects.filter(Q(username=login) | Q(email=login)).first()

        if user:
            attrs[self.username_field] = user.username

            if user.status != 'dealer':
                magazine = user.magazines.filter(is_active=True).first()
                if magazine:
                    if magazine.status not in ['hired', 'restored']:
                        raise serializers.ValidationError({'text': 'Вы пока не можете авторизоваться!'})

        data = super().validate(attrs)
        data['status'] = self.user.status
        data['user'] = self.user.id

        return data


class DealerMeInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ['email', 'pwd', 'name', 'image', 'phone', 'updated_at', 'id', 'firebase_token']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['profile'] = DealerProfileSerializer(instance.dealer_profile, context=self.context).data

        return representation


class DealerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        exclude = ['user', 'price_city', 'dealer_status', 'liability', 'id', 'managers', 'village', 'price_type',
                   'client_type']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        village = instance.village
        representation['city_title'] = village.city.title if village else None
        representation['city'] = village.city.id if village else None
        representation['stock'] = village.city.stocks.first().id if village else None

        return representation


class DealerStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerStore
        exclude = ('dealer',)

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


class DealerProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ['email', 'name', 'phone', 'image', 'id', 'firebase_token']

    # def update(self, instance, validated_data):
    #     username = validated_data.get('username')
    #     pwd = validated_data.get('pwd')
    #     if username:
    #         if not username_is_valid(username):
    #             raise serializers.ValidationError({"username": "Некорректный username"})
    #     if pwd:
    #         if not pwd_is_valid(pwd):
    #             raise serializers.ValidationError({"pwd": "Некорректный pwd"})
    #
    #     for key, value in validated_data.items():
    #         setattr(instance, key, value)
    #     pwd = validated_data.get('pwd')
    #     if pwd:
    #         instance.pwd = pwd
    #         instance.set_password(validated_data.get('pwd'))
    #     instance.save()
    #     return instance


class UserNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'status', 'image', 'is_read', 'title', 'description', 'link_id', 'created_at']

