from copy import deepcopy
from datetime import datetime

from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import transaction
from django.db.models import Sum, Q
from rest_framework import serializers
from transliterate import translit

from account.models import MyUser, DealerStatus, DealerProfile
from crm_general.models import CRMTaskFile, CRMTask
from general_service.models import Stock, City, PriceType, Village
from one_c.from_crm import sync_dealer_back_to_1C
from product.models import AsiaProduct, ProductImage, Category, Collection
from promotion.models import Story


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
        price = instance.prices.filter(price_type=user.dealer_profile.price_type,
                                       d_status=user.dealer_profile.dealer_status).first()
        if price:
            rep['price'] = price.price
        else:
            rep['price'] = instance.prices.filter(city=user.dealer_profile.price_city,
                                                  d_status=user.dealer_profile.dealer_status).first().price
        return rep


class StoryProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('image',)


class CRMUserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(validators=(UnicodeUsernameValidator(),), required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(validators=(validate_password,), required=True, write_only=True)

    class Meta:
        model = MyUser
        fields = ("id", "username", "email", "name", "image", "phone", "date_joined", "updated_at", "is_active",
                  "pwd", "password")
        read_only_fields = ("id", "pwd", "date_joined", "is_active")
        extra_kwargs = {
            "name": {"required": True},
            "phone": {"required": True}
        }

    def validate(self, attrs):
        # this place can be deleted since the manager._create_user and set_password methods do the same thing
        password = attrs.get("password")
        if password:
            attrs['pwd'] = password

        return attrs

    def create(self, validated_data):
        if MyUser.objects.filter(username=validated_data["username"]).exists():
            raise serializers.ValidationError({"username": "Пользователь с данным параметром уже существует!"})

        if MyUser.objects.filter(username=validated_data["email"]).exists():
            raise serializers.ValidationError({"username": "Пользователь с данным параметром уже существует!"})
        return super().create(validated_data)

    def update(self, instance, validated_data):
        for attr, value in deepcopy(validated_data).items():
            if getattr(instance, attr) == value:
                validated_data.pop(attr)

        username = validated_data.get('username')
        if username and MyUser.objects.exclude(id=instance.id).filter(username=username).exists():
            raise serializers.ValidationError({"username": "Пользователь с данным параметром уже существует!"})

        email = validated_data.get('email')
        if email and MyUser.objects.exclude(id=instance.id).filter(email=email).exists():
            raise serializers.ValidationError({"email": "Пользователь с данным параметром уже существует!"})

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

        # TODO: move validating user data to CRMUserSerializer
        if MyUser.objects.filter(username=user_data["username"]).exists():
            raise serializers.ValidationError(
                {"user": {"username": "Пользователь с данным параметром уже существует!"}}
            )

        if MyUser.objects.filter(email=user_data["email"]).exists():
            raise serializers.ValidationError(
                {"user": {"email": "Пользователь с данным параметром уже существует!"}}
            )

        validated_data['user'] = MyUser.objects.create_user(status=self._user_status, **user_data)
        # calling this method `create` should not return an error.
        # Therefore, the validation must be perfect,
        # otherwise if there is an error, the user will be created but the dealer profile will not
        return super().create(validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data:
            serializer = CRMUserSerializer(
                instance=instance.user,
                data=user_data,
                partial=self.partial,
                context=self.context
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return super().update(instance, validated_data)

    def save(self, **kwargs):
        profile = super().save(**kwargs)

        if profile.user.is_dealer:
            sync_dealer_back_to_1C(profile.user)
        return profile


class ActivitySerializer(serializers.Serializer):
    is_active = serializers.BooleanField(read_only=True, default=False)


class CRMCategorySerializer(serializers.ModelSerializer):
    crm_count = serializers.SerializerMethodField(read_only=True)
    orders_count = serializers.SerializerMethodField(read_only=True)
    count_1c = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Category
        fields = ("slug", "title", "is_active", "uid", "image", "crm_count", "orders_count", "count_1c")

    def get_stock_ids(self):
        return self.context.get("stock_ids", None)

    def get_crm_count(self, instance) -> int:
        stock_ids = self.get_stock_ids()
        return sum(
            instance.products.annotate(
                counts_sum=Sum(
                    "counts__count",
                    filter=Q(counts__stock_id__in=stock_ids) if stock_ids else None
                )
            ).values_list('counts_sum', flat=True)
        )

    def get_orders_count(self, instance) -> int:
        stock_ids = self.get_stock_ids()
        return sum(
            instance.products.annotate(
                orders_count=Sum(
                    'order_products__count',
                    filter=Q(
                        order_products__order__is_active=True,
                        order_products__order__status="paid",
                        order_products__order__stock_id__in=stock_ids,
                    ) if stock_ids else Q(
                        order_products__order__is_active=True,
                        order_products__order__status="paid",
                    )
                )
            ).values_list("orders_count", flat=True)
        )

    def get_count_1c(self, instance) -> int:
        return self.get_crm_count(instance) + self.get_orders_count(instance)


class CRMStockSerializer(serializers.ModelSerializer):
    city = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Stock
        exclude = ('is_show', 'is_active', 'uid')

    def get_city(self, instance):
        return instance.city.title


class CRMCitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ('title', 'slug', 'id')


class ABStockSerializer(serializers.ModelSerializer):
    city = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Stock
        exclude = ('is_show', 'is_active', 'uid', 'schedule')

    def get_city(self, instance):
        return instance.city.title


class CollectionCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = '__all__'

    def validate(self, attrs):
        title = translit(attrs['title'], 'ru', reversed=True)
        attrs['slug'] = title.replace(' ', '_').lower()
        return attrs


class CategoryCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

    def validate(self, attrs):
        title = translit(attrs['title'], 'ru', reversed=True)
        attrs['slug'] = title.replace(' ', '_').lower()
        return attrs


class CityListSerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = '__all__'


class StockListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = '__all__'


class DealerStatusListSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerStatus
        fields = '__all__'


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class UserImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ("image",)


class VerboseChoiceField(serializers.ChoiceField):
    def to_representation(self, value):
        return dict(self.choices).get(value, value)


class TaskFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRMTaskFile
        fields = ("file",)


class CityCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = '__all__'

    def validate(self, attrs):
        title = translit(attrs['title'], 'ru', reversed=True)
        attrs['slug'] = title.replace(' ', '_').lower()
        return attrs


class PriceTypeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceType
        fields = '__all__'


class DealerProfileSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DealerProfile
        fields = ('id', 'name')

    @staticmethod
    def get_name(obj):
        return obj.user.name


class ShortProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'title')


class CRMTaskCRUDSerializer(serializers.ModelSerializer):
    creator = serializers.CharField(read_only=True)

    class Meta:
        model = CRMTask
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['creator'] = CRMTaskUserSerializer(instance.creator, context=self.context).data
        rep['executors'] = CRMTaskUserSerializer(instance.executors, many=True, context=self.context).data
        rep['files'] = CRMTaskFileSerializer(instance.files, many=True, context=self.context).data

        return rep


class CRMTaskUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('id', 'name', 'status')


class CRMTaskFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRMTaskFile
        fields = '__all__'


class VillageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Village
        fields = ('id', 'title')
