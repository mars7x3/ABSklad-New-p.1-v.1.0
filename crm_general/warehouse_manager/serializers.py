from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from crm_general.models import CRMTask, CRMTaskFile, Inventory, InventoryProduct
from crm_general.serializers import VerboseChoiceField
from crm_general.warehouse_manager.utils import create_order_return_product
from general_service.models import Stock
from one_c.from_crm import sync_return_order_to_1C
from order.models import MyOrder, OrderProduct, ReturnOrderProduct, ReturnOrder, ReturnOrderProductFile
from product.models import AsiaProduct, Collection, Category, ProductImage, ProductSize


class ReturnOrderProductFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnOrderProductFile
        fields = ('id', 'file')


class ReturnOrderProductSerializer(serializers.ModelSerializer):
    files = ReturnOrderProductFileSerializer(many=True)
    title = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ReturnOrderProduct
        fields = '__all__'

    def get_title(self, instance):
        return instance.product.title


class WareHouseOrderProductSerializer(serializers.ModelSerializer):
    return_product_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = OrderProduct
        fields = '__all__'

    def get_return_product_count(self, instance):
        count = ReturnOrderProduct.objects.filter(product_id=instance.ab_product.id,
                                                  return_order__order_id=instance.order.id).aggregate(
            total_count=Sum('count'))['total_count']
        if count:
            return count
        return 0


class OrderListSerializer(serializers.ModelSerializer):
    type_status = VerboseChoiceField(choices=MyOrder.TYPE_STATUS)
    name = serializers.SerializerMethodField(read_only=True)
    creator_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MyOrder
        fields = '__all__'

    def get_name(self, instance):
        return instance.author.user.name

    def get_creator_name(self, instance):
        if instance.creator:
            return instance.creator.name


class OrderDetailSerializer(serializers.ModelSerializer):
    order_products = WareHouseOrderProductSerializer(read_only=True, many=True)
    type_status = VerboseChoiceField(choices=MyOrder.TYPE_STATUS)
    return_orders = serializers.SerializerMethodField()

    class Meta:
        model = MyOrder
        fields = '__all__'

    def get_return_orders(self, instance):
        return_order_instances = instance.return_orders.all()
        return ReturnOrderSerializer(return_order_instances, many=True).data

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['name'] = instance.author.user.name
        rep['creator_name'] = instance.creator.name if instance.creator else None
        return rep


class WareHouseCollectionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        user = self.context['request'].user
        stock_id = user.warehouse_profile.stock.id
        rep['categories_count'] = len(set(instance.products.values_list('category', flat=True)))
        products = instance.products.filter(counts__stock_id=stock_id)
        rep['products_count'] = sum(products.values_list('counts__count_crm', flat=True))
        return rep


class WareHouseCategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('title', 'is_active', 'id', 'slug')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context['request']
        stock_id = request.user.warehouse_profile.stock.id
        if self.context.get('retrieve'):
            products = instance.products.all()
            rep['products'] = WareHouseProductListSerializer(products, context={'request': request}, many=True).data
        else:
            rep['products_count'] = sum(instance.products.filter(counts__stock_id=stock_id).
                                        values_list('counts__count_crm', flat=True))
        return rep


class WareHouseProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'title', 'is_discount', 'vendor_code', 'created_at', 'category', 'collection', 'is_active')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        user = self.context['request'].user
        stock_id = user.warehouse_profile.stock.id
        rep['collection_name'] = instance.collection.title if instance.collection else None
        rep['category_name'] = instance.category.title if instance.category else None
        rep['stocks_count'] = sum(instance.counts.filter(stock_id=stock_id).values_list('count_crm', flat=True))
        cost_price = instance.cost_prices.filter(is_active=True).first()
        rep['cost_price'] = cost_price.price if cost_price else '---'
        naive_time = timezone.localtime().now()
        today = timezone.make_aware(naive_time)
        last_15_days = today - timezone.timedelta(days=15)
        rep['sot_15'] = round(sum((instance.order_products.filter(order__created_at__gte=last_15_days,
                                                                  order__is_active=True,
                                                                  order__status__in=['sent', 'paid', 'success'])
                                   .values_list('count', flat=True)), 2) / 15)
        avg_check = instance.order_products.filter(order__is_active=True,
                                                   order__status__in=['sent', 'success', 'paid', 'wait']
                                                   ).values_list('total_price', flat=True)

        if len(avg_check) == 0:
            rep['avg_check'] = 0
        else:
            rep['avg_check'] = round(sum(avg_check) / len(avg_check))

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


class InventoryProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryProduct
        exclude = ('inventory', )

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        product = instance.product
        stock = instance.inventory.sender.warehouse_profile.stock
        city = stock.city
        count_1c = sum(product.counts.filter(stock=stock).values_list('count_1c', flat=True))
        price = instance.product.prices.filter(city=city, product=product).first().price
        rep['product_title'] = instance.product.title
        rep['count_1c'] = count_1c
        rep['price'] = price
        rep['accounting_amount'] = count_1c * price
        return rep


class WareHouseInventorySerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField(read_only=True)
    receiver_name = serializers.SerializerMethodField(read_only=True)

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
            rep['products'] = InventoryProductSerializer(instance.products.all(), read_only=True, many=True).data
        return rep

    def update(self, instance, validated_data):
        products = self.context['request'].data.get('products')
        instance = super().update(instance, validated_data)
        if products:
            for product in products:
                inventory_product = InventoryProduct.objects.filter(product_id=product['product'],
                                                                    inventory=instance).first()
                if inventory_product:
                    inventory_product.count = product['count']
                    inventory_product.save()
                else:
                    ab_product = AsiaProduct.objects.filter(id=product['product']).first()
                    if ab_product is None:
                        raise serializers.ValidationError({'detail': 'Product not found'})
                    InventoryProduct.objects.create(inventory=instance, product=ab_product, count=product['count'])
        return instance

    @staticmethod
    def get_sender_name(obj):
        return obj.sender.name

    @staticmethod
    def get_receiver_name(obj):
        return obj.receiver.name if obj.receiver else None


class InventoryProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsiaProduct
        fields = ('id', 'title')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        stock_id = self.context.get('stock_id')
        stock = Stock.objects.get(id=stock_id)
        city = stock.city
        count_1c = sum(instance.counts.filter(stock=stock).values_list('count_1c', flat=True))
        price = instance.prices.filter(city=city).first().price
        rep['count_1c'] = count_1c
        rep['price'] = price
        rep['accounting_amount'] = count_1c * price
        return rep


class ReturnOrderSerializer(serializers.ModelSerializer):
    products = ReturnOrderProductSerializer(many=True, read_only=True)

    class Meta:
        model = ReturnOrder
        fields = '__all__'

    def validate(self, attrs):
        order_id = self.context['request'].data.get('order')
        order = MyOrder.objects.get(id=order_id)
        count = self.context['request'].data.get('count')
        order_product_ids = order.order_products.filter().values_list('ab_product__id', flat=True)
        product = int(self.context['request'].data.get('product'))
        if product not in order_product_ids:
            raise serializers.ValidationError({'detail': 'product not in order'})

        order_product = order.order_products.filter(ab_product_id=product).first()
        if int(count) > order_product.count:
            raise serializers.ValidationError({'detail': 'count can not be more than in order'})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request_body = self.context['request'].data
        order_id = request_body.get('order')
        comment = request_body.get('comment')
        count = request_body.get('count')
        product_id = request_body.get('product')
        files = self.context['request'].FILES.getlist('files')
        return_order = ReturnOrder.objects.filter(order_id=order_id).first()
        if return_order:
            return_product = create_order_return_product(return_order, comment, int(count), files, product_id)
            if return_product:
                return return_order
        else:
            instance = ReturnOrder.objects.create(**validated_data)
            return_product = create_order_return_product(instance, comment, int(count), files, product_id)
            if return_product:
                return instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['name'] = instance.order.author.user.name
        rep['status'] = instance.order.status
        return rep
