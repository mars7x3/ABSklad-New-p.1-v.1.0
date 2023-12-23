from django.db.models import Sumfrom rest_framework import serializersfrom account.models import MyUser, DealerStatus, CRMNotificationfrom crm_general.marketer.tasks import create_notificationsfrom general_service.serializers import CitySerializerfrom product.models import AsiaProduct, ProductImage, ProductSize, Collection, Categoryfrom promotion.models import Banner, Story, Motivation, Discountclass MarketerCollectionSerializer(serializers.ModelSerializer):    category_count = serializers.SerializerMethodField(read_only=True)    product_count = serializers.SerializerMethodField(read_only=True)    class Meta:        model = Collection        fields = '__all__'    @staticmethod    def get_product_count(obj):        return obj.products.count()    @staticmethod    def get_category_count(obj):        return obj.products.values('category').distinct().count()class MarketerCategorySerializer(serializers.ModelSerializer):    class Meta:        model = Category        fields = '__all__'    def to_representation(self, instance):        rep = super().to_representation(instance)        if self.context.get('retrieve'):            params = self.context['request'].query_params            products = instance.products.all()            discount = params.get('discount')            new_products = params.get('new')            search = params.get('search')            if discount:                products = products.filter(is_discount=True)            if new_products:                products = products.order_by('-created_at')            if search:                try:                    product_id = int(search)                    products = products.filter(uid=product_id)                except ValueError:                    products = products.filter(title__icontains=search)            rep['products'] = MarketerProductListSerializer(products, many=True).data        return repclass MarketerProductListSerializer(serializers.ModelSerializer):    price = serializers.SerializerMethodField(read_only=True)    count = serializers.SerializerMethodField(read_only=True)    avg_check = serializers.SerializerMethodField(read_only=True)    class Meta:        model = AsiaProduct        fields = ('id', 'title', 'is_active', 'price', 'count', 'is_discount', 'collection', 'category', 'avg_check')    @staticmethod    def get_price(obj):        first_price = obj.prices.first()        return first_price.price if first_price else None    @staticmethod    def get_count(obj):        return sum(obj.counts.all().values_list('count_crm', flat=True))    @staticmethod    def get_avg_check(obj):        avg_check = obj.order_products.filter(order__is_active=True,                                              order__status__in=['sent', 'success', 'paid', 'wait']                                              ).values_list('total_price', flat=True)        if len(avg_check) == 0:            return 0        return sum(avg_check) / len(avg_check)class MarketerProductSerializer(serializers.ModelSerializer):    collection = serializers.SerializerMethodField(read_only=True)    category = serializers.SerializerMethodField(read_only=True)    class Meta:        model = AsiaProduct        fields = '__all__'    def update(self, instance, validated_data):        images_to_delete = self.context['request'].data.get('images_to_delete')        images_to_save = self.context.get('request').FILES.getlist('images_to_save')        sizes = self.context['request'].data.get('sizes')        if images_to_delete:            images = instance.images.filter(id__in=images_to_delete)            images.delete()        if images_to_save:            images = [ProductImage(product=instance, image=image) for image in images_to_save]            ProductImage.objects.bulk_create(images)        if sizes:            for size in sizes:                product_size, created = ProductSize.objects.get_or_create(product=instance, id=size.get('id'),                                                                          defaults=sizes)                if not created:                    product_size.title = size.get('title', product_size.title)                    product_size.length = size.get('length', product_size.length)                    product_size.width = size.get('width', product_size.width)                    product_size.height = size.get('height', product_size.height)                    product_size.save()        return super().update(instance, validated_data)    def to_representation(self, instance):        rep = super().to_representation(instance)        rep['images'] = MarketerProductImageSerializer(instance.images.all(), many=True, context=self.context).data        rep['sizes'] = MarketerProductSizeSerializer(instance.sizes.all(), many=True, context=self.context).data        return rep    @staticmethod    def get_collection(obj):        return obj.collection.title    @staticmethod    def get_category(obj):        return obj.collection.titleclass ShortProductSerializer(serializers.ModelSerializer):    class Meta:        model = AsiaProduct        fields = ('id', 'title')class ParticipantsSerializer(serializers.ModelSerializer):    class Meta:        model = MyUser        fields = ('id', 'name', 'phone')class BannerListSerializer(serializers.ModelSerializer):    class Meta:        model = Banner        fields = '__all__'class BannerSerializer(serializers.ModelSerializer):    cities = CitySerializer(read_only=True, many=True)    products = MarketerProductListSerializer(read_only=True, many=True)    class Meta:        model = Banner        fields = '__all__'class MarketerProductImageSerializer(serializers.ModelSerializer):    class Meta:        model = ProductImage        fields = ('id', 'image')class MarketerProductSizeSerializer(serializers.ModelSerializer):    class Meta:        model = ProductSize        fields = '__all__'class DealerStatusSerializer(serializers.ModelSerializer):    class Meta:        model = DealerStatus        fields = '__all__'class StoryListSerializer(serializers.ModelSerializer):    class Meta:        model = Story        fields = '__all__'class StoryDetailSerializer(serializers.ModelSerializer):    products = ShortProductSerializer(read_only=True, many=True)    class Meta:        model = Story        fields = '__all__'class CRMNotificationSerializer(serializers.ModelSerializer):    class Meta:        model = CRMNotification        fields = '__all__'    def create(self, validated_data):        notifications_to_create = []        users = validated_data['users']        instance = super(CRMNotificationSerializer, self).create(validated_data)        for user in users:            notification_data = {                'user': user,                'notification': instance,                'title': validated_data.get('title'),                'description': validated_data.get('description'),                'status': validated_data.get('status'),                'link_id': validated_data.get('link_id')            }            notifications_to_create.append(notification_data)        image_full_url = str(instance.image.url).split('/')[-2:]        image_url = '/'.join(image_full_url)        dispatch_date = instance.dispatch_date        create_notifications(notifications_to_create, image_url=image_url, dispatch_date=dispatch_date)        return instanceclass MotivationSerializer(serializers.ModelSerializer):    class Meta:        model = Motivation        fields = ('id', 'title')class DiscountSerializer(serializers.ModelSerializer):    class Meta:        model = Discount        fields = ('id', 'title')