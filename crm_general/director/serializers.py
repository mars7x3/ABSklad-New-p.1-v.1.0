import datetime

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from account.models import MyUser, WarehouseProfile, ManagerProfile, RopProfile, Wallet, DealerProfile, BalanceHistory, \
    DealerStatus, DealerStore
from crm_general.director.utils import get_motivation_done
from crm_general.serializers import CRMCitySerializer, CRMStockSerializer, ABStockSerializer
from general_service.models import Stock, City
from order.models import MyOrder, Cart, CartProduct
from product.models import AsiaProduct, Collection, Category, ProductSize, ProductImage
from promotion.models import Discount, Motivation, MotivationPresent, MotivationCondition, ConditionCategory, \
    ConditionProduct


class StaffCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('id', 'username', 'status', 'phone', 'pwd', 'email', 'is_active', 'date_joined', 'image',
                  'updated_at', 'password', 'name')

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
        last_15_days = timezone.now() - timezone.timedelta(days=15)
        rep['sot_15'] = round(sum((instance.order_products.filter(order__created_at__gte=last_15_days,
                                                                  order__is_active=True,
                                                                  order__status__in=['Отправлено', 'Оплачено',
                                                                                     'Успешно'])
                                  .values_list('count'))) / 15, 2)
        rep['avg_check'] = sum(instance.order_products.filter(order__is_active=True,
                                                              order__status__in=['Отправлено', 'Успешно', 'Оплачено',
                                                                                 'Ожидание']
                                                              ).values_list('total_price', flat=True))

        return rep


class DirectorProductCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['sizes'] = DirectorProductSizeSerializer(instance.sizes.all(), many=True, context=self.context).data
        rep['images'] = DirectorProductImageSerializer(instance.images.all(), many=True, context=self.context).data
        return rep


class DirectorProductSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSize
        exclude = ('product', 'id')


class DirectorProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        exclude = ('product', 'position')


class DirectorDiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['products'] = DirectorDiscountProductSerializer(instance.products, many=True).data
        rep['cities'] = DirectorDiscountCitySerializer(instance.cities, many=True).data
        rep['dealer_statuses'] = DirectorDiscountDealerStatusSerializer(instance.dealer_statuses, many=True).data

        return rep


class DirectorDiscountProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'title')


class DirectorDiscountCitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ('id', 'title')


class DirectorDiscountDealerStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerStatus
        fields = ('id', 'title')


class DirectorDealerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        fields = ('city',)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get('request')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        start_date = timezone.make_aware(datetime.datetime.strptime(start_date, "%d-%m-%Y"))
        end_date = timezone.make_aware(datetime.datetime.strptime(end_date, "%d-%m-%Y"))
        rep['id'] = instance.user.id
        rep['name'] = instance.user.name
        rep['pds_amount'] = sum(instance.user.money_docs.filter(is_active=True, created_at__gte=start_date,
                                                                created_at__lte=end_date
                                                                ).values_list('amount', flat=True))
        rep['shipment_amount'] = sum(instance.orders.filter(is_active=True, status__in=['Успешно', 'Отправлено'],
                                                            released_at__gte=start_date, released_at__lte=end_date
                                                            ).values_list('price', flat=True))
        rep['city'] = instance.city.title if instance.city else '---'
        rep['status'] = True if instance.wallet.amount_crm > 50000 else False
        last_order = instance.orders.filter(is_active=True, status__in=['Успешно', 'Отправлено', 'Оплачено',
                                                                        'Ожидание']).last()
        rep['last_date'] = str(last_order.paid_at) if last_order else '---'
        rep['balance'] = instance.wallet.amount_crm

        return rep


class DirectorDealerCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('id', 'name', 'username', 'date_joined', 'email', 'phone', 'pwd', 'updated_at', 'password')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['profile'] = DirectorDealerProfileSerializer(instance.dealer_profile, context=self.context).data
        return rep

    def create(self, validated_data):
        with transaction.atomic():
            profile = self.context.get('request').data.get('profile')
            user = MyUser.objects.create_user(**validated_data)
            profile_serializer = DirectorDealerProfileSerializer(data=profile)
            profile_serializer.is_valid(raise_exception=True)
            profile_serializer.save(user=user)
            Wallet.objects.create(dealer=user.dealer_profile)
            return user

    def update(self, instance, validated_data):
        with transaction.atomic():
            profile = self.context.get('request').data.get('profile')
            for key, value in validated_data.items():
                setattr(instance, key, value)
            instance.pwd = validated_data.get('password')
            instance.set_password(validated_data.get('password'))
            instance.save()

            profile_serializer = DirectorDealerProfileSerializer(instance.dealer_profile, data=profile)
            profile_serializer.is_valid(raise_exception=True)
            profile_serializer.save()
            return instance


class DirectorDealerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        exclude = ('id', 'user')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['city_title'] = instance.city.title if instance.city else '---'
        rep['price_city_title'] = instance.price_city.title if instance.price_city else '---'
        rep['dealer_status'] = instance.dealer_status.title if instance.dealer_status else '---'
        rep['balance_crm'] = instance.wallet.amount_crm
        rep['balance_1c'] = instance.wallet.amount_1c
        rep['stores'] = DirectorDealerStoreSerializer(instance.dealer_stores, many=True, context=self.context).data
        rep['motivations'] = get_motivation_done(instance)

        return rep


class DirectorDealerStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerStore
        exclude = ('id', 'dealer')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['city_title'] = instance.city.title if instance.city else '---'
        return rep


class DirDealerMotivationPresentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MotivationPresent
        exclude = ('id', 'motivation')


class DirDealerOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyOrder
        fields = '__all__'


class DirDealerCartProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartProduct
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        price = instance.product.prices.filter(city=instance.cart.dealer.price_city,
                                               d_status=instance.cart.dealer.dealer_status).first()
        count = instance.product.counts.filter(stock=instance.cart.stock).first()
        rep['prod_title'] = instance.product.title
        rep['prod_category'] = instance.product.category.title
        rep['price'] = price.price * instance.count
        rep['discount_price'] = price.old_price - price.price * instance.count if price.discount > 0 else 0
        rep['crm_count'] = count.count_crm
        rep['stock_city'] = instance.stock.city.title

        return rep


class DirectorMotivationCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = Motivation
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['dealers'] = MotivationDealerSerializer(instance.dealers, many=True, context=self.context).data
        rep['conditions'] = MotivationConditionSerializer(instance.conditions, many=True, context=self.context).data

        return rep

    def create(self, validated_data):
        with transaction.atomic():
            conditions = self.context['request'].data['conditions']
            dealers = validated_data.pop('dealers')
            motivation = Motivation.objects.create(**validated_data)
            motivation.dealers.add(*dealers)
            motivation.save()
            MotivationCondition.objects.create(motivation=motivation, **conditions)

            return motivation

    def update(self, instance, validated_data):
        with transaction.atomic():
            profile = self.context.get('request').data.get('profile')
            for key, value in validated_data.items():
                setattr(instance, key, value)
            instance.pwd = validated_data.get('password')
            instance.set_password(validated_data.get('password'))
            instance.save()

            profile_serializer = DirectorDealerProfileSerializer(instance.dealer_profile, data=profile)
            profile_serializer.is_valid(raise_exception=True)
            profile_serializer.save()
            return instance


class MotivationDealerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        fields = ('id',)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['user_name'] = instance.user.name
        return rep


class MotivationConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MotivationCondition
        exclude = ('motivation',)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['condition_cats'] = MotivationConditionCategorySerializer(instance.condition_cats,
                                                                      many=True, context=self.context).data
        rep['condition_prods'] = MotivationConditionProductSerializer(instance.condition_prods,
                                                                      many=True, context=self.context).data
        rep['presents'] = MotivationPresentSerializer(instance.presents, many=True, context=self.context).data

        return rep


class MotivationConditionCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ConditionCategory
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['category_title'] = instance.category.title if instance.category else '---'
        return rep


class MotivationConditionProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConditionProduct
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['product_title'] = instance.product.title if instance.product else '---'
        return rep


class MotivationPresentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MotivationPresent
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['product_title'] = instance.product.title if instance.product else '---'
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
