import datetime

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from account.models import MyUser, DealerProfile, BalanceHistory, BalancePlus, BalancePlusFile
from crm_general.accountant.utils import deduct_returned_product_from_order_and_stock
from crm_general.models import Inventory, InventoryProduct
from crm_general.serializers import CRMStockSerializer

from general_service.models import Stock

from order.models import MyOrder, OrderReceipt, OrderProduct, ReturnOrder, ReturnOrderProduct, ReturnOrderProductFile
from product.models import AsiaProduct, Collection, Category


class MyOrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyOrder
        fields = ('author', 'id', 'status', 'type_status', 'price', 'created_at', 'released_at', 'paid_at')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['author_info'] = MyOrderDealerSerializer(instance.author, context=self.context).data
        rep['stock_title'] = instance.stock.title
        rep['creator_name'] = instance.creator.name if instance.creator else None
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


class MyOrderDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyOrder
        exclude = ('cost_price', 'uid')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['order_receipts'] = OrderReceiptSerializer(instance.order_receipts, many=True, context=self.context).data
        rep['author_info'] = MyOrderDealerSerializer(instance.author, context=self.context).data
        rep['order_products'] = OrderProductSerializer(instance.order_products, many=True, context=self.context).data
        rep['stock'] = CRMStockSerializer(instance.stock, context=self.context).data
        rep['creator_name'] = instance.creator.name if instance.creator else None
        return rep


class OrderReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderReceipt
        exclude = ('order',)


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
        fields = ('village', 'user')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['dealer_status'] = instance.dealer_status.title if instance.dealer_status else None
        rep['city'] = instance.village.city.title if instance.village else None
        rep['user_info'] = MyUserSerializer(instance.user, context=self.context).data
        rep['amount_crm'] = instance.wallet.amount_crm
        rep['amount_1c'] = instance.wallet.amount_1c
        rep['amount_paid'] = sum(instance.orders.filter(
            is_active=True, status__in=['paid', 'wait']).values_list('price', flat=True))
        last_trans = instance.user.money_docs.filter(is_active=True).last()
        rep['last_trans'] = last_trans.created_at if last_trans else None
        return rep


class MyUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('name', 'phone', 'email')


class DirBalanceHistorySerializer(serializers.ModelSerializer):
    files = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = BalanceHistory
        fields = '__all__'

    def get_files(self, obj):
        balance_plus_instance = BalancePlus.objects.filter(id=obj.action_id).first()
        files = BalancePlusFile.objects.filter(balance=balance_plus_instance)
        if files:
            serializer = BalancePlusFileSerializer(files, many=True, context=self.context)
            return serializer.data
        return []


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
        fields = ('village', 'user')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['user_info'] = MyUserSerializer(instance.user, context=self.context).data
        rep['city_title'] = instance.village.city.title if instance.village else None
        return rep


class AccountantProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'vendor_code', 'title', 'is_active', 'is_discount')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['collection_name'] = instance.collection.title if instance.collection else None
        rep['category_name'] = instance.category.title if instance.category else None
        stocks_count_crm = sum(instance.counts.all().values_list('count_crm', flat=True))
        rep['stocks_count_crm'] = stocks_count_crm
        rep['stocks_count_1c'] = sum(instance.counts.all().values_list('count_1c', flat=True))
        price = instance.prices.filter().first()
        rep['price'] = price.price if price else '---'
        rep['total_price'] = price.price * stocks_count_crm if price else 0
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
        rep['total_price'] = round(sum(instance.city.prices.all().values_list('price', flat=True)))
        rep['city_title'] = instance.city.title
        rep['stock'] = stocks_count_crm - stock
        return rep


class AccountantStockProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'vendor_code', 'title', 'is_active', 'is_discount')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        stock_id = self.context.get('stock_id')
        rep['collection_name'] = instance.collection.title if instance.collection else None
        rep['category_name'] = instance.category.title if instance.category else None
        stocks_count_crm = sum(instance.counts.filter(stock_id=stock_id).values_list('count_crm', flat=True))
        rep['stocks_count_crm'] = stocks_count_crm
        rep['stocks_count_1c'] = sum(instance.counts.filter(stock_id=stock_id).values_list('count_1c', flat=True))
        price = instance.prices.filter(city__stocks__id=stock_id).first()
        rep['price'] = price.price if price else '---'
        rep['total_price'] = price.price * stocks_count_crm if price else 0
        return rep


class AccountantStockDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ('id', 'title')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        products = instance.counts.all().values_list('product', flat=True)
        asia_products = AsiaProduct.objects.filter(pk__in=products)
        stock_id = instance.id
        rep['products'] = AccountantStockProductSerializer(asia_products, context={'stock_id': stock_id},
                                                           read_only=True, many=True).data
        return rep


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = ('id', 'status', 'is_active', 'created_at', 'updated_at', 'products', 'sender', 'receiver')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['sender_name'] = instance.sender.name if instance.sender else None
        rep['receiver_name'] = instance.receiver.name if instance.receiver else None
        rep['stock_title'] = instance.sender.warehouse_profile.stock.title
        rep['city_title'] = instance.sender.warehouse_profile.stock.city.title
        return rep


class AccountantStockShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ('id', 'title')


class InventoryProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryProduct
        fields = "__all__"

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        stock = instance.inventory.sender.warehouse_profile.stock
        city = stock.city
        product = instance.product
        rep['product'] = instance.product.id
        rep['product_id'] = instance.product.title
        count_1c = sum(product.counts.filter(stock=stock).values_list('count_1c', flat=True))
        price = instance.product.prices.filter(city=city, product=product).first().price
        rep['count_1c'] = count_1c
        rep['price'] = price
        rep['amount'] = instance.count * price
        rep['accounting_amount'] = count_1c * price
        return rep


class InventoryDetailSerializer(serializers.ModelSerializer):
    products = InventoryProductSerializer(many=True, read_only=True)

    class Meta:
        model = Inventory
        fields = ('id', 'status', 'is_active', 'created_at', 'updated_at', 'products', 'sender', 'receiver')

    def update(self, instance, validated_data):
        user = self.context['request'].user
        instance = super().update(instance, validated_data)
        instance.receiver = user
        instance.save()
        return instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['sender_name'] = instance.sender.name if instance.sender else None
        rep['receiver_name'] = instance.receiver.name if instance.receiver else None
        rep['stock_title'] = instance.sender.warehouse_profile.stock.title
        rep['city_title'] = instance.sender.warehouse_profile.stock.city.title
        rep['total_count'] = sum(instance.products.filter().values_list('count', flat=True))
        return rep


class ReturnOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnOrder
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['name'] = instance.order.author.user.name
        rep['status'] = instance.order.status
        return rep


class ReturnOrderProductFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnOrderProductFile
        fields = '__all__'


class ReturnOrderProductSerializer(serializers.ModelSerializer):
    files = ReturnOrderProductFileSerializer(many=True, read_only=True)
    title = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ReturnOrderProduct
        fields = '__all__'
        read_only_fields = ('count', 'price', 'comment', 'created_at', 'product', 'return_order', 'title')

    def update(self, instance, validated_data):
        if validated_data['status'] == 'success':
            deduct_returned_product_from_order_and_stock(order=instance.return_order.order,
                                                         product_id=instance.product.id,
                                                         count=instance.count)
        return super().update(instance, validated_data)

    def get_title(self, instance):
        return instance.product.title


class ReturnOrderDetailSerializer(serializers.ModelSerializer):
    products = ReturnOrderProductSerializer(many=True, read_only=True)
    order = MyOrderDetailSerializer(read_only=True)

    class Meta:
        model = ReturnOrder
        fields = '__all__'
