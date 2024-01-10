import datetime

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from account.models import MyUser, WarehouseProfile, ManagerProfile, RopProfile, Wallet, DealerProfile, BalanceHistory, \
    DealerStatus, DealerStore
from crm_general.director.tasks import create_product_prices
from crm_general.director.utils import get_motivation_margin, kpi_info, get_motivation_done, verified_director
from crm_general.models import CRMTask, CRMTaskFile, CRMTaskResponse, CRMTaskResponseFile, CRMTaskGrade, KPI, KPIItem

from crm_general.serializers import CRMCitySerializer, CRMStockSerializer, ABStockSerializer
from general_service.models import Stock, City, StockPhone, PriceType
from order.models import MyOrder, Cart, CartProduct
from product.models import AsiaProduct, Collection, Category, ProductSize, ProductImage, ProductPrice, ProductCount

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

    def create(self, validated_data):
        with transaction.atomic():
            request = self.context['request']
            user = MyUser.objects.create_user(**validated_data)

            if user.status == 'manager':
                city_id = request.data.get('city')
                ManagerProfile.objects.create(user=user, city_id=city_id)

            elif user.status == 'rop':
                rop_profile = RopProfile.objects.create(user=user)
                cities = request.data.get('cities', [])
                cities = City.objects.filter(id__in=cities)
                rop_profile.cities.add(*cities)

            elif user.status == 'warehouse':
                stock_id = request.data.get('stock')
                WarehouseProfile.objects.create(user=user, stock_id=stock_id)

            return user

    def update(self, instance, validated_data):
        with transaction.atomic():
            request = self.context['request']
            for key, value in validated_data.items():
                setattr(instance, key, value)
            instance.pwd = validated_data.get('password')
            instance.set_password(validated_data.get('password'))
            instance.save()

            if instance.status == 'manager':
                manager_profile = instance.manager_profile
                manager_profile.city_id = request.data.get('city')
                manager_profile.save()

            elif instance.status == 'rop':
                city_ids = request.data.get('cities', [])
                cities = City.objects.filter(id__in=city_ids)
                rop_profile = instance.rop_profile
                rop_profile.cities.clear()
                rop_profile.cities.add(*cities)
                rop_profile.save()

            elif instance.status == 'warehouse':
                warehouse_profile = instance.warehouse_profile
                warehouse_profile.stock_id = request.data.get('stock')
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
        last_transaction = instance.balance_histories.filter(is_active=True, amount__gte=0).last()
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
        last_15_days = timezone.now() - timezone.timedelta(days=15)
        rep['sot_15'] = round(sum((instance.order_products.filter(order__created_at__gte=last_15_days,
                                                                  order__is_active=True,
                                                                  order__status__in=['sent', 'paid',
                                                                                     'success'])
                                   .values_list('count'))) / 15, 2)
        avg_check = instance.order_products.filter(order__is_active=True,
                                                   order__status__in=['sent', 'success', 'paid', 'wait']
                                                   ).values_list('total_price', flat=True)
        rep['avg_check'] = sum(avg_check) / len(avg_check)

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
        rep['is_active'] = instance.user.is_active
        rep['name'] = instance.user.name
        balance_histories = instance.balance_histories.filter(is_active=True, created_at__gte=start_date,
                                                              created_at__lte=end_date)
        rep['pds_amount'] = sum(balance_histories.filter(status='wallet').values_list('amount', flat=True))
        rep['shipment_amount'] = sum(balance_histories.filter(status='order').values_list('amount', flat=True))
        rep['balance'] = balance_histories.last().balance if balance_histories else 0

        rep['city'] = instance.city.title if instance.city else '---'
        rep['status'] = True if instance.wallet.amount_crm > 50000 else False
        last_order = instance.orders.filter(is_active=True, status__in=['success', 'sent', 'paid',
                                                                        'wait']).last()
        rep['last_date'] = str(last_order.paid_at) if last_order else '---'

        return rep


class DirectorDealerCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('id', 'name', 'username', 'date_joined', 'email', 'phone', 'pwd', 'updated_at', 'password',
                  'image')

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
        rep['dealer_status_title'] = instance.dealer_status.title if instance.dealer_status else '---'
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


class DirBalanceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BalanceHistory
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
        with transaction.atomic():
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
        rep['prices'] = DirectorProductPriceListSerializer(instance.prices.filter(d_status__discount=0),
                                                           many=True, context=self.context).data
        return rep


class DirectorProductPriceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPrice
        fields = ('price', 'price_type')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['price_type_title'] = instance.price_type.title if instance.price_type else '---'
        return rep


class DirectorTaskCRUDSerializer(serializers.ModelSerializer):
    creator = serializers.CharField(read_only=True)

    class Meta:
        model = CRMTask
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['creator'] = DirectorTaskUserSerializer(instance.creator, context=self.context).data
        rep['files'] = DirectorTaskFileSerializer(instance.files, many=True, context=self.context).data
        rep['responses'] = DirectorTaskResponseSerializer(instance.task_responses, many=True, context=self.context).data

        return rep

    def validate(self, attrs):
        attrs['creator'] = self.context['request'].user
        return attrs

    def create(self, validated_data):
        executors = self.context['request'].data.getlist('executors')
        files = self.context['request'].FILES.getlist('files')
        task = CRMTask.objects.create(**validated_data)

        files_list = []
        for f in files:
            files_list.append(CRMTaskFile(file=f, task=task))
        CRMTaskFile.objects.bulk_create(files_list)

        executors_list = []
        for e in executors:
            executors_list.append(CRMTaskResponse(executor_id=e, task=task))
        CRMTaskResponse.objects.bulk_create(executors_list)
        return task

    def update(self, instance, validated_data):
        executors = self.context['request'].data.getlist('executors')
        files = self.context['request'].FILES.getlist('files')
        delete_files = self.context['request'].data.getlist('delete_files')

        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()

        if delete_files:
            instance.files.filter(id__in=delete_files).delete()

        files_list = []
        for f in files:
            files_list.append(CRMTaskFile(file=f, task=instance))
        CRMTaskFile.objects.bulk_create(files_list)

        executors_list = []
        for e in executors:
            executors_list.append(CRMTaskResponse(executor_id=e, task=instance))
        instance.task_responses.all().delete()
        CRMTaskResponse.objects.bulk_create(executors_list)
        return instance


class DirectorTaskResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRMTaskResponse
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['executor'] = DirectorTaskUserSerializer(instance.executor, context=self.context).data
        rep['files'] = DirectorTaskFileSerializer(instance.response_files.all(), many=True, context=self.context).data
        rep['grade'] = instance.grade.title if instance.grade else '---'

        return rep


class DirectorTaskResponseFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRMTaskResponseFile
        fields = '__all__'


class DirectorTaskFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRMTaskFile
        fields = '__all__'


class DirectorTaskUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('id', 'name', 'status')


class DirectorCRMTaskGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRMTaskGrade
        fields = '__all__'


class DirectorTaskListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRMTask
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['creator'] = DirectorTaskUserSerializer(instance.creator, context=self.context).data
        rep['files'] = DirectorTaskFileSerializer(instance.files, many=True, context=self.context).data
        executors = instance.task_responses.values_list('executor__name', 'executor__status')
        executors = [{"name": i[0], "status": i[-1]} for i in executors]
        rep['executors'] = executors

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


class DirectorStockCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        exclude = ('uid', 'is_show')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['city_title'] = instance.city.title if instance.city else '---'
        rep['warehouses'] = StockWarehouseSerializer(instance.warehouse_profiles, many=True, context=self.context).data
        rep['phones'] = StockPhoneSerializer(instance.phones, many=True, context=self.context).data
        rep['managers'] = StockManagerSerializer(instance.city.manager_profiles, many=True, context=self.context).data

        return rep

    def create(self, validated_data):
        phones = self.context['request'].data['phones']
        stock = Stock.objects.create(**validated_data)
        phones_list = []
        for p in phones:
            phones_list.append(StockPhone(stock=stock, phone=p['phone']))
        StockPhone.objects.bulk_create(phones_list)
        return stock

    def update(self, instance, validated_data):
        phones = self.context['request'].data['phones']
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        phones_list = []
        for p in phones:
            phones_list.append(StockPhone(stock=instance, phone=p['phone']))
        instance.phones.all().delete()
        StockPhone.objects.bulk_create(phones_list)
        return instance


class StockPhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockPhone
        fields = ('phone',)


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
        rep['collection'] = instance.collection.title if instance.category else '---'
        stock = Stock.objects.get(id=stock_id)
        price = instance.prices.filter(city=stock.city).first()
        rep['prod_amount_crm'] = instance.total_count * price.price
        rep['prod_count_crm'] = instance.total_count
        rep['norm_count'] = instance.total_count - instance.norm_count
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


class WarehouseListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('name', 'id')




