from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from crm_general.models import CRMTaskResponse, CRMTask, CRMTaskFile, CRMTaskResponseFile, Inventory, InventoryProduct
from crm_general.serializers import VerboseChoiceField
from order.models import MyOrder, OrderProduct
from product.models import AsiaProduct, Collection, Category, ProductImage, ProductSize


class WareHouseOrderProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderProduct
        fields = '__all__'


class OrderListSerializer(serializers.ModelSerializer):
    type_status = VerboseChoiceField(choices=MyOrder.TYPE_STATUS)

    class Meta:
        model = MyOrder
        fields = '__all__'


class OrderDetailSerializer(serializers.ModelSerializer):
    order_products = WareHouseOrderProductSerializer(read_only=True, many=True)
    type_status = VerboseChoiceField(choices=MyOrder.TYPE_STATUS)

    class Meta:
        model = MyOrder
        fields = '__all__'


class WareHouseCollectionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['categories_count'] = len(set(instance.products.values_list('category', flat=True)))
        rep['products_count'] = sum(instance.products.values_list('counts__count_crm', flat=True))
        return rep


class WareHouseCategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('title', 'is_active', 'id', 'slug')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if self.context.get('retrieve'):
            products = instance.products.all()
            rep['products'] = WareHouseProductListSerializer(products, many=True).data
        else:
            rep['products_count'] = sum(instance.products.values_list('counts__count_crm', flat=True))
        return rep


class WareHouseProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'title', 'is_active', 'is_discount', 'vendor_code', 'created_at', 'category', 'collection')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['collection_name'] = instance.collection.title
        rep['category_name'] = instance.category.title
        rep['stocks_count'] = sum(instance.counts.all().values_list('count_crm', flat=True))
        cost_price = instance.cost_prices.filter(is_active=True).first()
        rep['cost_price'] = cost_price.price if cost_price else '---'

        last_15_days = timezone.now() - timezone.timedelta(days=15)
        rep['sot_15'] = round(sum((instance.order_products.filter(order__created_at__gte=last_15_days,
                                                                  order__is_active=True,
                                                                  order__status__in=['sent', 'paid', 'success'])
                                   .values_list('count', flat=True))), 2) / 15
        avg_check = instance.order_products.filter(order__is_active=True,
                                                   order__status__in=['sent', 'success', 'paid', 'wait']
                                                   ).values_list('total_price', flat=True)

        if len(avg_check) == 0:
            rep['avg_check'] = 0
        else:
            rep['avg_check'] = sum(avg_check) / len(avg_check)

        return rep


class WareHouseProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['images'] = MarketerProductImageSerializer(instance.images.all(), many=True, context=self.context).data
        rep['sizes'] = MarketerProductSizeSerializer(instance.sizes.all(), many=True, context=self.context).data
        return rep


class MarketerProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'image')


class MarketerProductSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSize
        fields = '__all__'


class WareHouseTaskFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRMTaskFile
        fields = ('id', 'file')


class WareHouseTaskSerializer(serializers.ModelSerializer):
    files = WareHouseTaskFileSerializer(many=True, read_only=True)

    class Meta:
        model = CRMTask
        fields = '__all__'


class WareHouseCRMTaskResponseFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CRMTaskResponseFile
        fields = '__all__'


class WareHouseCRMTaskResponseSerializer(serializers.ModelSerializer):
    task = WareHouseTaskSerializer(read_only=True)
    files = WareHouseCRMTaskResponseFileSerializer(many=True, read_only=True, source='response_files')

    class Meta:
        model = CRMTaskResponse
        fields = '__all__'


class InventoryProductSerializer(serializers.ModelSerializer):
    product_title = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = InventoryProduct
        exclude = ('inventory', )

    @staticmethod
    def get_product_title(obj):
        return obj.product.title


class WareHouseInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = '__all__'

    def create(self, validated_data):
        sender = self.context.get('request').user
        instance = Inventory.objects.create(sender=sender, **validated_data)

        products = self.context['request'].data.get('products')
        inventory_products = []

        for obj in products:
            product = AsiaProduct.objects.get(id=obj['product'])
            inventory_product = InventoryProduct(
                inventory=instance,
                product=product,
                count=obj['count']
            )
            inventory_products.append(inventory_product)

        InventoryProduct.objects.bulk_create(inventory_products)
        return instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if self.context.get('retrieve'):
            rep['products'] = InventoryProductSerializer(instance.products.all(),  read_only=True, many=True).data
        return rep


class InventoryProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'title')
