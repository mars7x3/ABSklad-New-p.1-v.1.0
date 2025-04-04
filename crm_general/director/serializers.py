import datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from account.models import MyUser, WarehouseProfile, ManagerProfile, RopProfile, Wallet, DealerProfile, \
    DealerStatus, DealerStore
from account.utils import username_is_valid, pwd_is_valid
from crm_general.director.tasks import create_product_prices
from crm_general.director.utils import get_motivation_margin, kpi_info, get_motivation_done, verified_director, \
    create_product_counts_for_stock, create_prod_counts
from crm_general.models import CRMTask, CRMTaskFile, KPI, KPIItem

from crm_general.serializers import CRMCitySerializer, CRMStockSerializer, ABStockSerializer
from crm_kpi.models import DealerKPI
from promotion.utils import calculate_discount
from crm_general.utils import change_dealer_profile_status_after_deactivating_dealer_status
from general_service.models import Stock, City, StockPhone, PriceType
from one_c.from_crm import sync_dealer_back_to_1C, sync_product_crm_to_1c, sync_stock_1c_2_crm, sync_category_crm_to_1c
from order.models import MyOrder, Cart, CartProduct, OrderProduct
from product.models import AsiaProduct, Collection, Category, ProductSize, ProductImage, ProductPrice, ProductCount, \
    ProductCostPrice

from promotion.models import Discount, Motivation, MotivationPresent, MotivationCondition, ConditionCategory, \
    ConditionProduct


class StaffCRUDSerializer(serializers.ModelSerializer):
    only_wh_in_stock = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MyUser
        fields = ('id', 'username', 'status', 'phone', 'pwd', 'email', 'is_active', 'date_joined', 'image',
                  'updated_at', 'password', 'name', 'only_wh_in_stock')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.status == 'rop':
            rep['profile'] = RopProfileSerializer(instance.rop_profile, context=self.context).data
        if instance.status == 'warehouse':
            rep['profile'] = WarehouseProfileSerializer(instance.warehouse_profile, context=self.context).data
        return rep

    def create(self, validated_data):
        request = self.context['request']
        user = MyUser.objects.create_user(**validated_data)
        is_main = request.data.get('is_main')
        if user.status == 'rop':
            rop_profile = RopProfile.objects.create(user=user)
            cities = request.data.get('cities', [])
            cities = City.objects.filter(id__in=cities)
            rop_profile.cities.add(*cities)

        elif user.status == 'warehouse':
            stock_id = request.data.get('stock')
            WarehouseProfile.objects.create(user=user, stock_id=stock_id, is_main=is_main)

        return user

    def update(self, instance, validated_data):
        request = self.context['request']
        for key, value in validated_data.items():
            setattr(instance, key, value)
        # instance.pwd = validated_data.get('password')
        # instance.set_password(validated_data.get('password'))
        instance.save()

        if instance.status == 'rop':
            city_ids = request.data.get('cities', [])
            cities = City.objects.filter(id__in=city_ids)
            rop_profile = instance.rop_profile
            rop_profile.cities.clear()
            rop_profile.cities.add(*cities)
            rop_profile.save()

        elif instance.status == 'warehouse':
            warehouse_profile = instance.warehouse_profile
            warehouse_profile.stock_id = request.data.get('stock')
            warehouse_profile.is_main = request.data.get('is_main')
            warehouse_profile.save()

        return instance

    @staticmethod
    def get_only_wh_in_stock(obj):
        if obj.status == 'warehouse':
            try:
                profile = WarehouseProfile.objects.filter(user=obj).first()
                stock = profile.stock
                count = stock.warehouse_profiles.filter(user__is_active=True).count()
                return True if count < 2 else False
            except AttributeError:
                return False
        return None


class WarehouseProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseProfile
        exclude = ('id', 'user')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['stock'] = ABStockSerializer(instance.stock, context=self.context).data
        return rep


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('id', 'name')


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
        fields = ('dealer_status', 'village')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['status_title'] = instance.dealer_status.title if instance.dealer_status else '---'
        rep['city_title'] = instance.village.city.title if instance.village else '---'
        rep['name'] = instance.user.name
        rep['user_id'] = instance.user.id
        last_transaction = instance.user.money_docs.filter(is_active=True).last()
        rep['last_repl'] = last_transaction.created_at if last_transaction else '---'

        return rep


class DirectorProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'title', 'is_active', 'collection', 'category', 'is_discount', 'vendor_code')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['collection_title'] = instance.collection.title if instance.collection else '---'
        rep['category_title'] = instance.category.title if instance.category else '---'
        rep['stocks_count'] = sum(instance.counts.all().values_list('count_crm', flat=True))
        cost_price = instance.cost_prices.filter(is_active=True).first()
        rep['cost_price'] = cost_price.price if cost_price else '---'
        rep['verified'] = verified_director(instance)

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
        naive_time = timezone.localtime().now()
        today = timezone.make_aware(naive_time)
        last_15_days = today - timezone.timedelta(days=15)
        rep['sot_15'] = round(sum((instance.order_products.filter(order__created_at__gte=last_15_days,
                                                                  order__is_active=True,
                                                                  order__status__in=['sent', 'paid', 'success'])
                                   .values_list('count', flat=True))) / 15, 2)
        avg_check = round(instance.order_products.filter(order__is_active=True,
                                                         order__status__in=['sent', 'success', 'paid', 'wait']
                                                         ).values_list('total_price', flat=True))
        if len(avg_check) == 0:
            rep['avg_check'] = 0
        else:
            rep['avg_check'] = sum(avg_check) / len(avg_check)

        return rep


class StockProductCountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        exclude = ('is_show', 'is_active', 'uid', 'schedule')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        product_id = self.context.get('product_id')
        rep['city_title'] = instance.city.title
        rep['product_count'] = (ProductCount.objects.filter(stock=instance, product_id=product_id)
                                .aggregate(total_count=Sum('count_crm')))
        return rep


class DirectorProductCRUDSerializer(serializers.ModelSerializer):
    stocks = serializers.SerializerMethodField()

    class Meta:
        model = AsiaProduct
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        cost_prices = instance.cost_prices.filter(is_active=True).first()
        rep['cost_price'] = cost_prices.price if cost_prices else '---'
        # rep['sizes'] = DirectorProductSizeSerializer(instance.sizes.all(), many=True, context=self.context).data
        # rep['images'] = DirectorProductImageSerializer(instance.images.all(), many=True, context=self.context).data

        rep['city_prices'] = DirectorProductPriceListSerializer(instance.prices.filter(d_status__discount=0,
                                                                                       city__isnull=False),
                                                                many=True, context=self.context).data

        rep['type_prices'] = DirectorProductPriceListSerializer(instance.prices.filter(d_status__discount=0,
                                                                                       price_type__isnull=False),
                                                                many=True, context=self.context).data
        rep['stock_counts'] = StockProductCountSerializer(Stock.objects.all(), many=True,
                                                          context={'product_id': instance.id}).data
        return rep

    @staticmethod
    def get_stocks(instance):
        counts_instances = instance.counts.all()
        stocks_data = []

        for count_norm_instance in counts_instances:
            stock_instance = count_norm_instance.stock
            if stock_instance:
                stocks_data.append({
                    'stock_id': stock_instance.id,
                    'stock_title': stock_instance.title,
                    'count_norm': count_norm_instance.count_norm
                })
        return stocks_data

    def update(self, instance, validated_data):
        request = self.context['request']
        date = timezone.localtime().now()
        aware_date = timezone.make_aware(date)
        stocks = request.data.get('stocks')
        cost_price = request.data.get('cost_price')
        type_prices = request.data.get('type_prices')
        city_prices = request.data.get('city_prices')
        is_active = validated_data.get('is_active', True)
        if not is_active:
            discounts = Discount.objects.filter(is_active=True)
            for discount in discounts:
                products = discount.products.all()
                if instance in products:
                    raise serializers.ValidationError(
                        'Невозможно деактивировать продукт который находится в активной акции'
                    )
            kpi_product = DealerKPI.objects.filter(is_confirmed=True, kpi_products__product_id=instance.id,
                                                   month__month=aware_date.month, month__year=aware_date.year)
            if kpi_product:
                raise serializers.ValidationError(
                    'Невозможно деактивировать продукт который находится в активном KPI'
                )

        if stocks:
            stock_norm_counts_to_update = []
            for s in stocks:
                product_count = ProductCount.objects.get(product=instance, stock=s['stock_id'])
                product_count.count_norm = s['count_norm']
                stock_norm_counts_to_update.append(product_count)
            ProductCount.objects.bulk_update(stock_norm_counts_to_update, ['count_norm'])

        if city_prices:
            if instance.is_discount:
                raise serializers.ValidationError({'detail': 'Can not change price for discounted product'})
            city_prices_to_update = []
            dealer_statuses = DealerStatus.objects.all()
            for price in city_prices:
                for d_status in dealer_statuses:
                    product_price = ProductPrice.objects.get(id=price.get('id'))
                    product_d_status_price = ProductPrice.objects.filter(city_id=price.get('city'),
                                                                         product=instance,
                                                                         d_status=d_status).first()
                    discount_price = calculate_discount(price.get('price'), d_status.discount)
                    product_d_status_price.price = discount_price
                    product_price.price = price.get('price')
                    city_prices_to_update.append(product_price)
                    city_prices_to_update.append(product_d_status_price)
            ProductPrice.objects.bulk_update(city_prices_to_update, ['price'])
        if type_prices:
            if instance.is_discount:
                raise serializers.ValidationError({'detail': 'Can not change price for discounted product'})
            type_prices_to_update = []
            dealer_statuses = DealerStatus.objects.all()
            for price in type_prices:
                for d_status in dealer_statuses:
                    product_price = ProductPrice.objects.get(id=price.get('id'))
                    product_d_status_price = ProductPrice.objects.filter(price_type_id=price.get('price_type'),
                                                                         product=instance,
                                                                         d_status=d_status).first()
                    if product_d_status_price:
                        discount_price = calculate_discount(price.get('price'), d_status.discount)
                        product_d_status_price.price = discount_price
                        type_prices_to_update.append(product_d_status_price)
                    product_price.price = price.get('price')
                    type_prices_to_update.append(product_price)
            ProductPrice.objects.bulk_update(type_prices_to_update, ['price'])

        if cost_price:
            product_cost_price = instance.cost_prices.filter(is_active=True).first()
            if product_cost_price:
                product_cost_price.price = cost_price
                product_cost_price.save()
            else:
                ProductCostPrice.objects.create(product=instance, price=cost_price, is_active=True)

        instance = super().update(instance, validated_data)
        sync_product_crm_to_1c(instance)
        return instance


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
        dealer_profiles_data = rep.get('dealer_profiles', [])

        dealer_profiles_list = [
            {'id': profile.id, 'name': profile.user.name}
            for profile in DealerProfile.objects.filter(id__in=dealer_profiles_data)
        ]
        rep['dealer_profiles'] = dealer_profiles_list

        return rep

    def update(self, instance, validated_data):
        products = validated_data.get('products', [])
        if instance.is_active and products:
            crn_products = instance.products.all()
            for product in crn_products:
                if product not in products:
                    raise serializers.ValidationError({'detail': 'Cannot delete products from an active Discount'})
        return super().update(instance, validated_data)


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
        fields = ('village',)

    def to_representation(self, instance):
        rep = super().to_representation(instance)

        rep['id'] = instance.user.id
        rep['is_active'] = instance.user.is_active
        rep['name'] = instance.user.name
        rep['city'] = instance.village.city.title if instance.village else '---'
        return rep


class DirectorDealerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        exclude = ('id', 'user')

    def validate(self, attrs):
        village = attrs.pop("village", None)
        if village:
            attrs["village_id"] = village.id

        d_status = attrs.pop("dealer_status", None)
        if d_status:
            attrs["dealer_status_id"] = d_status.id

        price_city = attrs.pop("price_city", None)
        if price_city:
            attrs["price_city_id"] = price_city.id

        price_type = attrs.pop("price_type", None)
        if price_type:
            attrs["price_type_id"] = price_type.id
        return attrs

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['city_title'] = instance.village.city.title if instance.village else '---'
        rep['price_city_title'] = instance.price_city.title if instance.price_city else '---'
        rep['dealer_status_title'] = instance.dealer_status.title if instance.dealer_status else '---'
        rep['balance_crm'] = instance.wallet.amount_crm
        rep['balance_1c'] = instance.wallet.amount_1c
        rep['stores'] = DirectorDealerStoreSerializer(instance.dealer_stores.all(), many=True, context=self.context).data
        return rep


class DirectorDealerCRUDSerializer(serializers.ModelSerializer):
    profile = DirectorDealerProfileSerializer(many=False, required=True, source="dealer_profile")

    class Meta:
        model = MyUser
        fields = ('id', 'name', 'username', 'date_joined', 'email', 'phone', 'pwd', 'updated_at', 'password',
                  'image', 'is_active', 'status', 'profile')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['managers'] = DirectorStaffListSerializer(instance.dealer_profile.managers.all(),
                                                      many=True, context=self.context).data

        return rep

    def create(self, validated_data):
        # username = validated_data.get('username')
        # pwd = validated_data.get('password')
        # if username:
        #     if not username_is_valid(username):
        #         raise serializers.ValidationError({"username": "Некорректный username"})
        # if pwd:
        #     if not pwd_is_valid(pwd):
        #         raise serializers.ValidationError({"password": "Некорректный password"})
        profile = validated_data.pop("profile")
        user = MyUser.objects.create_user(**validated_data)
        DealerProfile.objects.create(**profile, user=user)
        sync_dealer_back_to_1C(user)
        return user

    def update(self, instance, validated_data):
        profile = validated_data.pop("profile", None)
        instance = super().update(instance, validated_data)

        if profile:
            dealer_profile = instance.dealer_profile

            for field, value in profile.items():
                setattr(dealer_profile, field, value)

            dealer_profile.save()

        sync_dealer_back_to_1C(instance)
        return instance


class DirectorDealerStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerStore
        exclude = ('id', 'dealer')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['city_title'] = instance.city
        return rep


class DirectorMotivationDealerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        fields = ('id', 'user',)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['name'] = instance.user.name
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
        price = instance.product.prices.filter(price_type=instance.cart.dealer.price_type,
                                               d_status=instance.cart.dealer.dealer_status).first()
        if not price:
            price = instance.product.prices.filter(city=instance.cart.dealer.price_city,
                                                   d_status=instance.cart.dealer.dealer_status).first()

        count = instance.product.counts.filter(stock=instance.cart.stock).first()
        rep['prod_title'] = instance.product.title
        rep['prod_category'] = instance.product.category.title
        rep['price'] = price.price * instance.count
        rep['discount_price'] = price.old_price - price.price * instance.count if price.discount > 0 else 0
        rep['crm_count'] = count.count_crm
        rep['stock_city'] = instance.cart.stock.city.title

        return rep


class DirectorMotivationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Motivation
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['margin'] = get_motivation_margin(instance)

        return rep


class DirectorMotivationDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Motivation
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['margin'] = get_motivation_margin(instance)

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
        conditions = self.context['request'].data['conditions']
        dealers = validated_data.pop('dealers')

        motivation = Motivation.objects.create(**validated_data)
        motivation.dealers.add(*dealers)
        motivation.save()

        condition_cats = []
        condition_prods = []
        presents = []

        for c in conditions:
            condition = MotivationCondition.objects.create(motivation=motivation, status=c['status'],
                                                           money=c['money'], text=c['text'])
            match c['status']:
                case 'category':
                    for cat in c['condition_cats']:
                        condition_cats.append(ConditionCategory(condition=condition, count=cat['count'],
                                                                category_id=cat['category']))

                case 'product':
                    for prod in c['condition_prods']:
                        condition_prods.append(ConditionProduct(condition=condition, count=prod['count'],
                                                                product_id=prod['product']))
            for pres in c['presents']:
                presents.append(MotivationPresent(
                    condition=condition, status=pres['status'], money=pres['money'], text=pres['text'],
                    expense=pres['expense']
                ))
        ConditionCategory.objects.bulk_create(condition_cats)
        ConditionProduct.objects.bulk_create(condition_prods)
        MotivationPresent.objects.bulk_create(presents)

        return motivation

    def update(self, instance, validated_data):
        with transaction.atomic():
            conditions = self.context['request'].data['conditions']
            dealers = validated_data.pop('dealers')
            motivation = instance
            if motivation.is_active:
                if timezone.now() > motivation.start_date:
                    serializers.ValidationError('Активные мотивации нельзя изменять!')
            for key, value in validated_data.items():
                setattr(motivation, key, value)
            motivation.dealers.clear()
            motivation.dealers.add(*dealers)
            motivation.save()
            motivation.conditions.all().delete()

            condition_cats = []
            condition_prods = []
            presents = []

            for c in conditions:
                condition = MotivationCondition.objects.create(motivation=motivation, status=c['status'],
                                                               money=c['money'], text=c['text'])
                match c['status']:
                    case 'category':
                        for cat in c['condition_cats']:
                            condition_cats.append(ConditionCategory(condition=condition, count=cat['count'],
                                                                    category_id=cat['category']))

                    case 'product':
                        for prod in c['condition_prods']:
                            condition_prods.append(ConditionProduct(condition=condition, count=prod['count'],
                                                                    product_id=prod['product']))
                for pres in c['presents']:
                    presents.append(MotivationPresent(
                        condition=condition, status=pres['status'], money=pres['money'], text=pres['text']
                    ))

            ConditionCategory.objects.bulk_create(condition_cats)
            ConditionProduct.objects.bulk_create(condition_prods)
            MotivationPresent.objects.bulk_create(presents)

            return motivation


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


class DirectorPriceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'title')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        cost_price = instance.cost_prices.filter(is_active=True).last()
        rep['cost_price'] = cost_price.price if cost_price else '---'
        request = self.context['request']
        price_type = request.query_params.get('price_type')
        price_city = request.query_params.get('price_city')

        if price_type:
            rep['prices'] = DirectorProductPriceListSerializer(instance.prices.filter(d_status__discount=0,
                                                                                      price_type__isnull=False),
                                                               many=True, context=self.context).data
        if price_city:
            rep['prices'] = DirectorProductPriceListSerializer(instance.prices.filter(d_status__discount=0,
                                                                                      city__isnull=False),
                                                               many=True, context=self.context).data
        return rep


class DirectorProductPriceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPrice
        fields = ('id', 'price', 'price_type', 'city')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['price_type_title'] = instance.price_type.title if instance.price_type else None
        rep['city_title'] = instance.city.title if instance.city else None

        return rep


class DirectorTaskCRUDSerializer(serializers.ModelSerializer):
    creator = serializers.CharField(read_only=True)

    class Meta:
        model = CRMTask
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['creator'] = DirectorTaskUserSerializer(instance.creator, context=self.context).data
        rep['executors'] = DirectorTaskUserSerializer(instance.executors, many=True, context=self.context).data
        rep['files'] = DirectorTaskFileSerializer(instance.files, many=True, context=self.context).data

        return rep

    def validate(self, attrs):
        attrs['creator'] = self.context['request'].user
        return attrs

    def create(self, validated_data):
        files = self.context['request'].FILES.getlist('files')
        executors = validated_data.pop('executors')
        task = CRMTask.objects.create(**validated_data)
        task.executors.set(executors)
        task.save()
        files_list = []
        for f in files:
            files_list.append(CRMTaskFile(file=f, task=task))
        CRMTaskFile.objects.bulk_create(files_list)

        return task

    def update(self, instance, validated_data):
        files = self.context['request'].FILES.getlist('files')
        delete_files = self.context['request'].data.get('delete_files')
        if delete_files:
            delete_files = self.context['request'].data.getlist('delete_files')
        executors = validated_data.get('executors')
        if executors:
            executors = validated_data.pop('executors')

        for key, value in validated_data.items():
            setattr(instance, key, value)
        if executors:
            instance.executors.set(executors)
        instance.save()

        if delete_files:
            instance.files.filter(id__in=delete_files).delete()

        files_list = []
        for f in files:
            files_list.append(CRMTaskFile(file=f, task=instance))
        CRMTaskFile.objects.bulk_create(files_list)

        return instance


class DirectorTaskFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRMTaskFile
        fields = '__all__'


class DirectorTaskUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('id', 'name', 'status')


class DirectorTaskListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRMTask
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['creator'] = DirectorTaskUserSerializer(instance.creator, context=self.context).data
        rep['executors'] = DirectorTaskUserSerializer(instance.executors, many=True, context=self.context).data
        rep['files'] = DirectorTaskFileSerializer(instance.files, many=True, context=self.context).data

        return rep


class StockWarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseProfile
        fields = ('user',)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['name'] = instance.user.name
        return rep


class StockManagerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerProfile
        fields = ('user',)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['name'] = instance.user.name
        return rep


class StockPhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockPhone
        fields = ('phone',)


class ValidateStockSerializer(serializers.ModelSerializer):
    phones = StockPhoneSerializer(many=True, required=True)

    class Meta:
        model = Stock
        exclude = ('uid', 'is_show')

    def validate(self, attrs):
        city = attrs.pop("city", None)
        if city:
            attrs["city_id"] = city
        return attrs

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['city_title'] = instance.city.title if instance.city else '---'
        rep['warehouses'] = StockWarehouseSerializer(instance.warehouse_profiles, many=True, context=self.context).data
        return rep


class DirectorStockCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        exclude = ('uid', 'is_show')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['city_title'] = instance.city.title if instance.city else '---'
        rep['warehouses'] = StockWarehouseSerializer(instance.warehouse_profiles, many=True, context=self.context).data
        rep['phones'] = StockPhoneSerializer(instance.phones, many=True, context=self.context).data

        return rep

    def create(self, validated_data):
        phones = self.context['request'].data['phones']
        stock = Stock.objects.create(**validated_data)
        # create_product_counts_for_stock(stock=stock)
        phones_list = []
        for p in phones:
            phones_list.append(StockPhone(stock=stock, phone=p['phone']))
        StockPhone.objects.bulk_create(phones_list)
        sync_stock_1c_2_crm(stock)
        create_prod_counts(stock)

        return stock

    def update(self, instance, validated_data):
        phones = self.context['request'].data.get('phones')
        if phones:
            for key, value in validated_data.items():
                setattr(instance, key, value)
            instance.save()
            phones_list = []
            for p in phones:
                phones_list.append(StockPhone(stock=instance, phone=p['phone']))
            instance.phones.all().delete()
            StockPhone.objects.bulk_create(phones_list)
            return instance
        instance = super().update(instance, validated_data)
        sync_stock_1c_2_crm(instance)
        return instance


class StockListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        exclude = ('uid', 'is_show')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['city_title'] = instance.city.title if instance.city else '---'
        rep['warehouses'] = StockWarehouseSerializer(instance.warehouse_profiles, many=True, context=self.context).data
        rep['prod_amount_crm'] = instance.total_sum
        rep['prod_count_crm'] = instance.total_count
        rep['norm_count'] = instance.total_count - instance.norm_count
        return rep


class StockProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'title', 'collection', 'category', 'vendor_code', 'is_active')

    def to_representation(self, instance):
        stock_id = self.context['request'].query_params.get('stock')
        rep = super().to_representation(instance)
        rep['category_title'] = instance.category.title if instance.category else '---'
        rep['collection'] = instance.collection.title if instance.collection else '---'
        stock = Stock.objects.get(id=stock_id)
        price = instance.prices.filter(city=stock.city).first()
        rep['prod_amount_crm'] = instance.total_count * price.price
        rep['prod_count_crm'] = instance.total_count
        rep['norm_count'] = instance.norm_count
        return rep


class DirectorDealerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('status', 'name', 'id')


class DirectorStaffListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('status', 'name', 'id')


class DirectorKPIStaffListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('status', 'name')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.status == 'manager':
            rep['city_title'] = instance.manager_profile.city.title
            rep['city'] = instance.manager_profile.city.slug

        return rep


class DirectorKPICRUDSerializer(serializers.ModelSerializer):
    author = serializers.CharField(read_only=True)

    class Meta:
        model = KPI
        fields = "__all__"

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['kpi_items'] = DirectorKKPIItemSerializer(instance.kpi_items, many=True, context=self.context).data
        rep['executor_info'] = DirectorKPIStaffListSerializer(instance.executor, context=self.context).data

        return rep

    def create(self, validated_data):
        items = self.context['request'].data['items']
        validated_data['author'] = self.context['request'].user
        kpi = KPI.objects.create(**validated_data)
        for item in items:
            product_ids = item.pop('products', None)
            category_ids = item.pop('categories', None)
            kpi_item = KPIItem.objects.create(kpi=kpi, **item)

            if product_ids:
                products = AsiaProduct.objects.filter(id__in=product_ids)
                kpi_item.products.clear()
                kpi_item.products.add(*products)

            if category_ids:
                categories = Category.objects.filter(id__in=category_ids)
                kpi_item.categories.clear()
                kpi_item.categories.add(*categories)

        return kpi

    def update(self, instance, validated_data):
        items = self.context['request'].data['items']
        validated_data['author'] = self.context['request'].user
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        kpi = instance
        kpi.kpi_items.all().delete()
        for item in items:
            product_ids = item.pop('products', None)
            category_ids = item.pop('categories', None)
            kpi_item = KPIItem.objects.create(kpi=kpi, **item)

            if product_ids:
                products = AsiaProduct.objects.filter(id__in=product_ids)
                kpi_item.products.clear()
                kpi_item.products.add(*products)

            if category_ids:
                categories = Category.objects.filter(id__in=category_ids)
                kpi_item.categories.clear()
                kpi_item.categories.add(*categories)

        return kpi


class DirectorKKPIItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = KPIItem
        exclude = ('kpi', 'id')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['products'] = KPIAsiaProductSerializer(instance.products, many=True, context=self.context).data
        rep['categories'] = KPICategorySerializer(instance.categories, many=True, context=self.context).data
        return rep


class KPIAsiaProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'title')


class KPICategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'slug', 'title')


class DirectorKPIListSerializer(serializers.ModelSerializer):
    class Meta:
        model = KPI
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['kpi_info'] = kpi_info(instance)
        rep['executor_info'] = KPIExecutorSerializer(instance.executor, context=self.context).data

        return rep


class KPIExecutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('id', 'name', 'status')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.status == 'manager':
            rep['city'] = instance.manager_profile.city.title if instance.manager_profile.city else '---'
        else:
            rep['city'] = '---'
        return rep


class PriceTypeCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceType
        fields = '__all__'

    def create(self, validated_data):
        price_type = PriceType.objects.create(**validated_data)
        create_product_prices(price_type.id)
        return price_type

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()

        if instance.is_active is False:
            for d in instance.dealer_profiles.all():
                d.price_type.delete()
        return instance


class WarehouseListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('name', 'id')


class DirectorDealerStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerStatus
        fields = '__all__'

    def validate(self, attrs):
        discount = attrs['discount']
        zero_discount = DealerStatus.objects.filter(discount=0).first()
        if discount == 0:
            if zero_discount:
                raise serializers.ValidationError({'detail': 'Dealer status with discount 0 already exists'})
        return attrs

    def create(self, validated_data):
        cities = City.objects.all()
        price_types = PriceType.objects.all()

        dealer_status = super().create(validated_data)
        discount_amount = Decimal(dealer_status.discount)

        product_prices_to_create = []

        for city in cities:
            for product in AsiaProduct.objects.all():
                product_base_price = ProductPrice.objects.filter(product=product,
                                                                 city=city,
                                                                 d_status__discount=0).first()
                base_price = Decimal(product_base_price.price)

                discounted_price = base_price - (base_price * (discount_amount / 100))

                product_price_data = {
                    'product': product,
                    'city': city,
                    'd_status': dealer_status,
                    'price': discounted_price,
                    'old_price': base_price,
                    'price_type': None,
                }
                product_prices_to_create.append(product_price_data)
        ProductPrice.objects.bulk_create([ProductPrice(**data) for data in product_prices_to_create])

        product_type_prices_to_create = []

        for price_type in price_types:
            for product in AsiaProduct.objects.all():
                product_base_price = ProductPrice.objects.filter(product=product,
                                                                 price_type=price_type,
                                                                 d_status__discount=0).first()
                base_price = Decimal(product_base_price.price)

                discounted_price = base_price - (base_price * (discount_amount / 100))

                product_price_data = {
                    'product': product,
                    'city': None,
                    'd_status': dealer_status,
                    'price': discounted_price,
                    'old_price': base_price,
                    'price_type': price_type,
                }
                product_type_prices_to_create.append(product_price_data)
        ProductPrice.objects.bulk_create([ProductPrice(**data) for data in product_type_prices_to_create])
        return dealer_status

    def update(self, instance, validated_data):
        if instance.discount == 0:
            raise serializers.ValidationError({'detail': 'Permission denied!'})
        product_prices = instance.prices.all()
        new_discount_amount = validated_data['discount']
        new_discount_amount = Decimal(new_discount_amount)

        product_prices_to_update = []
        for product_price in product_prices:
            if product_price.price_type:
                product_base_price = ProductPrice.objects.filter(product__id=product_price.product.id,
                                                                 price_type=product_price.price_type,
                                                                 d_status__discount=0).first()
            else:
                product_base_price = ProductPrice.objects.filter(product__id=product_price.product.id,
                                                                 city=product_price.city,
                                                                 d_status__discount=0).first()
            base_price = Decimal(product_base_price.price)

            discounted_price = base_price - (base_price * (new_discount_amount / 100))
            product_price.price = discounted_price
            product_price.old_price = base_price
            product_prices_to_update.append(product_price)
        ProductPrice.objects.bulk_update(product_prices_to_update, ['price', 'old_price'])

        instance = super().update(instance, validated_data)
        if not instance.is_active:
            dealers = DealerProfile.objects.filter(dealer_status=instance)
            change_dealer_profile_status_after_deactivating_dealer_status(dealers)
        return instance


class DirectorCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

    def create(self, validated_data):
        category = Category.objects.create(**validated_data)
        sync_category_crm_to_1c(category)
        return category

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        sync_category_crm_to_1c(instance)
        return instance


class DirectorOrderDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyOrder
        exclude = ('gmail', 'name', 'phone', 'address', 'comment', 'uid', 'main_order', 'is_active', 'updated_at',
                   )

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['author_info'] = MyOrderDealerSerializer(instance.author, context=self.context).data
        rep['products'] = MyOrderProductSerializer(instance.order_products, many=True, context=self.context).data
        rep['stock'] = CRMStockSerializer(instance.stock, context=self.context).data
        return rep


class MyOrderDealerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        fields = ('village', 'user')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['name'] = instance.user.name
        rep['city_title'] = instance.village.city.title if instance.village else None
        rep['phone'] = instance.user.phone
        return rep


class MyOrderProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderProduct
        fields = ('count', 'price', 'total_price')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['prod_info'] = OrderAsiaProductSerializer(instance.ab_product, context=self.context).data
        return rep


class OrderAsiaProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'title', 'category')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['category_title'] = instance.category.title if instance.category else None
        return rep


