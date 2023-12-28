import datetime

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from account.models import MyUser, DealerProfile, BalanceHistory, BalancePlus
from order.models import MyOrder, OrderReceipt, OrderProduct
from product.models import AsiaProduct


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
        return rep


class BalancePlusDealerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        fields = ('city', 'user')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['user_info'] = MyUserSerializer(instance.user, context=self.context).data
        rep['city_title'] = instance.city.title if instance.city else None
        return rep
