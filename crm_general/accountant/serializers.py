import datetime

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from account.models import MyUser, DealerProfile, BalanceHistory, BalancePlus, BalancePlusFile

from general_service.models import Stock

from order.models import MyOrder, OrderReceipt, OrderProduct
from product.models import AsiaProduct, Collection, Category


class MyOrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyOrder
        fields = ('author', 'id', 'status', 'type_status', 'price')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['author_info'] = MyOrderDealerSerializer(instance.author, context=self.context).data

        return rep


class MyOrderDealerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        fields = ('city', 'user')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['name'] = instance.user.name
        rep['city_title'] = instance.city.title if instance.city else None
        return rep


class MyOrderDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyOrder
        exclude = ('cost_price', 'uid')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['order_receipts'] = OrderReceiptSerializer(instance.order_receipts, many=True, context=self.context).data
        rep['author_info'] = MyOrderDealerSerializer(instance.author, context=self.context).data
        rep['order_products'] = OrderProductSerializer(instance.order_products, many=True, context=self.context).data

        return rep


class OrderReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderReceipt
        exclude = ('order', 'uid')


class OrderProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderProduct
        exclude = ('order', 'cost_price', 'discount', 'category')

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


class DealerProfileListSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        fields = ('city', 'user')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['dealer_status'] = instance.dealer_status.title if instance.dealer_status else None
        rep['city'] = instance.city.title if instance.city else None
        rep['user_info'] = MyUserSerializer(instance.user, context=self.context).data
        rep['amount_crm'] = instance.wallet.amount_crm
        rep['amount_1c'] = instance.wallet.amount_1c
        rep['amount_paid'] = sum(instance.orders.filter(is_active=True, status__in=['paid', 'wait']).values_list('price'))
        last_trans = instance.user.money_docs.filter(is_active=True).last()
        rep['last_trans'] = last_trans.created_at if last_trans else None
        return rep


class MyUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('name', 'phone', 'email')


class DirBalanceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BalanceHistory
        fields = '__all__'


class BalancePlusListSerializer(serializers.ModelSerializer):
    class Meta:
        model = BalancePlus
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['user_info'] = BalancePlusDealerSerializer(instance.dealer, context=self.context).data
        rep['files'] = BalancePlusFileSerializer(instance.files, many=True, context=self.context).data
        return rep


class BalancePlusFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BalancePlusFile
        fields = ('file',)


class BalancePlusDealerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        fields = ('city', 'user')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['user_info'] = MyUserSerializer(instance.user, context=self.context).data
        rep['city_title'] = instance.city.title if instance.city else None
        return rep


class AccountantProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'vendor_code', 'title', 'is_active', 'is_discount')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['collection_name'] = instance.collection.title
        rep['category_name'] = instance.category.title
        stocks_count_crm = sum(instance.counts.all().values_list('count_crm', flat=True))
        stock = sum(instance.counts.all().values_list('count_norm', flat=True))
        rep['stocks_count_crm'] = stocks_count_crm
        rep['stocks_count_1c'] = sum(instance.counts.all().values_list('count_1c', flat=True))
        price = instance.prices.filter().first()
        rep['price'] = price.price if price else '---'
        rep['total_price'] = sum(instance.prices.all().values_list('price', flat=True))
        rep['stock'] = stocks_count_crm - stock
        return rep


class AccountantCollectionSerializer(serializers.ModelSerializer):
    category_count = serializers.SerializerMethodField(read_only=True)
    product_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Collection
        fields = '__all__'

    @staticmethod
    def get_product_count(obj):
        return sum(obj.products.all().values_list('counts__count_crm', flat=True))

    @staticmethod
    def get_category_count(obj):
        return obj.products.values('category').distinct().count()


class AccountantCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if self.context.get('retrieve'):
            params = self.context['request'].query_params
            products = instance.products.all()
            discount = params.get('discount')
            new_products = params.get('new')
            search = params.get('search')

            if discount:
                products = products.filter(is_discount=True)
            if new_products:
                products = products.order_by('-created_at')
            if search:
                products = products.filter(title__icontains=search)
            rep['products'] = AccountantProductSerializer(products, many=True).data
        rep['products_count_crm'] = sum(instance.products.values_list('counts__count_crm', flat=True))
        rep['products_count_1c'] = sum(instance.products.values_list('counts__count_1c', flat=True))
        return rep


class AccountantStockListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        warehouse_profiles = instance.warehouse_profiles.values_list('user__name')
        profiles = [name for names in warehouse_profiles for name in names]
        rep['managers'] = profiles
        stocks_count_crm = sum(instance.counts.all().values_list('count_crm', flat=True))
        stock = sum(instance.counts.all().values_list('count_norm', flat=True))
        rep['stocks_count_crm'] = stocks_count_crm
        rep['stocks_count_1c'] = sum(instance.counts.all().values_list('count_1c', flat=True))
        rep['total_price'] = sum(instance.city.prices.all().values_list('price', flat=True))
        rep['city_title'] = instance.city.title
        rep['stock'] = stocks_count_crm - stock
        return rep


class AccountantStockDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ('id', 'title')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        products = instance.counts.all().values_list('product', flat=True)
        asia_products = AsiaProduct.objects.filter(pk__in=products)
        rep['products'] = AccountantProductSerializer(asia_products, read_only=True, many=True).data
        return rep
      