from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from account.models import MyUser, DealerProfile, StaffProfile
from general_service.models import City
from order.models import MyOrder, OrderReceipt


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("slug", "title",)


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(validators=(validate_password,), required=True, write_only=True)

    class Meta:
        model = MyUser
        fields = ("id", "username", "email", "date_joined", "is_active", "pwd", "password")
        read_only_fields = ("id", "pwd", "date_joined", "is_active")


class DealerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, required=True)
    city = CitySerializer(many=False, read_only=True)

    class Meta:
        model = DealerProfile
        fields = ('user', 'name', 'city', 'dealer_status', 'phone', 'liability', 'price_city')

    def validate(self, attrs):
        attrs['city'] = self.context['request'].user.staff_profile.city
        return attrs

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        validated_data['user'] = MyUser.objects.create_user(status="dealer", **user_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data:
            serializer = UserSerializer(instance=instance.user, data=user_data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return super().update(instance, validated_data)


class StaffProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, required=True)
    city = CitySerializer(many=False, read_only=True)

    class Meta:
        model = StaffProfile
        fields = ("user", "name", "city", "phone")

    def validate(self, attrs):
        user = self.context['request'].user
        attrs['city'] = user.staff_profile.city
        attrs['stock'] = user.staff_profile.stock
        return attrs

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        validated_data['user'] = MyUser.objects.create_user(status="warehouse", **user_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data:
            serializer = UserSerializer(instance=instance.user, data=user_data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return super().update(instance, validated_data)


class OrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyOrder
        fields = ("id", "status", "name", "gmail", "address", "price", "type_status", "created_at", "paid_at",
                  "released_at")


class OrderReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderReceipt
        fields = ("order", "file", "created_at")



class OrderSerializer(serializers.ModelSerializer):


    class Meta:
        model = MyOrder
        fields = ("id", "status", "name", "gmail", "address", "price", "type_status", "created_at", "paid_at",
                  "released_at", "phone")
