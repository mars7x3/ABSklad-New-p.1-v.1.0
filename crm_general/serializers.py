from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from account.models import MyUser
from product.models import AsiaProduct, ProductImage
from promotion.models import TargetPresent, Target, Story


class StaffListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('id', 'image')


class StoryDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['products'] = StoryProductSerializer(instance.products.all(),
                                                 many=True, context=self.context).data
        return rep


class StoryProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'description', 'avg_rating', 'reviews_count')

    def to_representation(self, instance):
        user = self.context.get('request').user
        rep = super().to_representation(instance)
        rep['images'] = StoryProductImageSerializer(instance.images.first(), context=self.context).data
        rep['price'] = instance.prices.filter(city=user.dealer_profile.price_city,
                                              d_status=user.dealer_profile.dealer_status).first().price
        return rep


class StoryProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('image',)


class TargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Target
        exclude = ('dealer', 'id')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['presents'] = TargetPresentSerializer(instance.presents.all(), many=True, context=self.context).data

        return rep


class TargetPresentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TargetPresent
        exclude = ('id', 'target')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['product'] = TargetPresentProductSerializer(instance.product).data

        return rep


class TargetPresentProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('title',)


class CRMUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(validators=(validate_password,), required=True, write_only=True)

    class Meta:
        model = MyUser
        fields = ("id", "username", "email", "name", "image", "phone", "date_joined", "updated_at", "is_active",
                  "pwd", "password")
        read_only_fields = ("id", "pwd", "date_joined", "is_active")

    def validate(self, attrs):
        # this place can be deleted since the manager._create_user and set_password methods do the same thing
        password = attrs.get("password")
        if password:
            attrs['pwd'] = password
        return attrs

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)


class BaseProfileSerializer(serializers.ModelSerializer):
    user = CRMUserSerializer(many=False, required=True)

    @property
    def _user_status(self):
        status = getattr(getattr(self, 'Meta'), 'user_status', None)
        assert status, '%s.Meta must include `user_status`' % self.__class__.__name__
        return status

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        validated_data['user'] = MyUser.objects.create_user(status=self._user_status, **user_data)
        # calling this method `create` should not return an error.
        # Therefore, the validation must be perfect,
        # otherwise if there is an error, the user will be created but the dealer profile will not
        return super().create(validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data:
            serializer = CRMUserSerializer(instance=instance.user, data=user_data, partial=True, context=self.context)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return super().update(instance, validated_data)


class ActivitySerializer(serializers.Serializer):
    active = serializers.BooleanField(read_only=True, default=False)
