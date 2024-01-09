import jsonfrom datetime import datetimefrom django.db.models import Sumfrom django.utils import timezonefrom rest_framework import serializersfrom account.models import MyUser, DealerStatus, CRMNotification, DealerProfilefrom crm_general.marketer.tasks import create_notificationsfrom crm_general.models import CRMTaskResponse, CRMTaskResponseFile, CRMTask, CRMTaskFilefrom product.models import AsiaProduct, ProductImage, ProductSize, Collection, Categoryfrom promotion.models import Banner, Story, Motivation, Discountclass MarketerCollectionSerializer(serializers.ModelSerializer):    category_count = serializers.SerializerMethodField(read_only=True)    product_count = serializers.SerializerMethodField(read_only=True)    class Meta:        model = Collection        fields = '__all__'    @staticmethod    def get_product_count(obj):        return sum(obj.products.all().values_list('counts__count_crm', flat=True))    @staticmethod    def get_category_count(obj):        return obj.products.values('category').distinct().count()class MarketerCategorySerializer(serializers.ModelSerializer):    class Meta:        model = Category        fields = '__all__'    def to_representation(self, instance):        rep = super().to_representation(instance)        if self.context.get('retrieve'):            params = self.context['request'].query_params            products = instance.products.all()            discount = params.get('discount')            new_products = params.get('new')            search = params.get('search')            if discount:                products = products.filter(is_discount=True)            if new_products:                products = products.order_by('-created_at')            if search:                try:                    product_id = int(search)                    products = products.filter(uid=product_id)                except ValueError:                    products = products.filter(title__icontains=search)            rep['products'] = MarketerProductListSerializer(products, many=True).data        rep['products_count'] = sum(instance.products.values_list('counts__count_crm', flat=True))        return repclass MarketerProductListSerializer(serializers.ModelSerializer):    cost_price = serializers.SerializerMethodField(read_only=True)    avg_check = serializers.SerializerMethodField(read_only=True)    sot_15 = serializers.SerializerMethodField(read_only=True)    class Meta:        model = AsiaProduct        fields = (            'id', 'vendor_code', 'title', 'is_active', 'cost_price', 'created_at', 'is_discount', 'collection',            'category', 'avg_check',            'sot_15')    @staticmethod    def get_cost_price(obj):        first_price = obj.cost_prices.filter(is_active=True).first()        return first_price.price if first_price else None    @staticmethod    def get_avg_check(obj):        avg_check = obj.order_products.filter(order__is_active=True,                                              order__status__in=['sent', 'success', 'paid', 'wait']                                              ).values_list('total_price', flat=True)        if len(avg_check) == 0:            return 0        return sum(avg_check) / len(avg_check)    @staticmethod    def get_sot_15(obj):        last_15_days = timezone.now() - timezone.timedelta(days=15)        sot_15 = round(sum((obj.order_products.filter(order__created_at__gte=last_15_days,                                                      order__is_active=True,                                                      order__status__in=['sent', 'paid', 'success'])                            .values_list('count', flat=True))), 2) / 15        return sot_15    def to_representation(self, instance):        rep = super().to_representation(instance)        rep['category_name'] = instance.category.title if instance.category else None        rep['collection_name'] = instance.collection.title if instance.collection else None        return repclass MarketerProductSerializer(serializers.ModelSerializer):    class Meta:        model = AsiaProduct        fields = '__all__'    def update(self, instance, validated_data):        images = self.context['request'].data.get('images_to_delete')        if images:            images_to_delete = self.context['request'].data.getlist('images_to_delete')            if images_to_delete:                images = instance.images.filter(id__in=images_to_delete)                images.delete()        images_to_save = self.context.get('request').FILES.getlist('images_to_save')        sizes = self.context['request'].data.get('sizes')        if images_to_save:            first_position = ProductImage.objects.filter(product=instance, position=1)            if first_position:                images = [ProductImage(product=instance, image=image) for image in images_to_save]            else:                first_image = images_to_save.pop(0)                ProductImage.objects.create(product=instance, image=first_image, position=1)                images = [ProductImage(product=instance, image=image) for image in images_to_save]            ProductImage.objects.bulk_create(images)        if sizes:            if type(sizes) is str:                sizes = json.loads(sizes)            for size in sizes:                if size.get('id'):                    product_size = ProductSize.objects.get(product=instance, id=size.get('id'))                    product_size.title = size.get('title', product_size.title)                    product_size.length = size.get('length', product_size.length)                    product_size.width = size.get('width', product_size.width)                    product_size.height = size.get('height', product_size.height)                    product_size.save()                else:                    ProductSize.objects.create(product=instance, title=size.get('title'), length=size.get('length'),                                               width=size.get('width'), height=size.get('height'))        return super().update(instance, validated_data)    def to_representation(self, instance):        rep = super().to_representation(instance)        rep['images'] = MarketerProductImageSerializer(instance.images.all(), many=True, context=self.context).data        rep['sizes'] = MarketerProductSizeSerializer(instance.sizes.all(), many=True, context=self.context).data        return repclass ShortProductSerializer(serializers.ModelSerializer):    class Meta:        model = AsiaProduct        fields = ('id', 'title')class ParticipantsSerializer(serializers.ModelSerializer):    class Meta:        model = MyUser        fields = ('id', 'name', 'phone')class DealerProfileSerializer(serializers.ModelSerializer):    name = serializers.SerializerMethodField(read_only=True)    class Meta:        model = DealerProfile        fields = ('id', 'name')    @staticmethod    def get_name(obj):        return obj.user.nameclass BannerListSerializer(serializers.ModelSerializer):    class Meta:        model = Banner        fields = '__all__'    def create(self, validated_data):        discount = validated_data.get('discount')        if discount:            start_time = discount.start_date            end_time = discount.end_date            start_time = datetime.combine(start_time, datetime.min.time())            end_time = datetime.combine(end_time, datetime.min.time())            discount_products = discount.products.all()            discount_dealers = discount.dealer_profiles.all()            banner = Banner.objects.create(start_time=start_time, end_time=end_time, **validated_data)            banner.products.set(discount_products)            banner.dealer_profiles.set(discount_dealers)            return banner        else:            products = validated_data.pop('products', None)            dealers = validated_data.pop('dealers', None)            banner = super(BannerListSerializer, self).create(validated_data)            if products:                banner.products.set(products)            if dealers:                banner.dealer_profiles.set(dealers)            return bannerclass BannerSerializer(serializers.ModelSerializer):    class Meta:        model = Banner        fields = '__all__'    def to_representation(self, instance):        rep = super(BannerSerializer, self).to_representation(instance)        dealer_profiles_data = rep.get('dealer_profiles', [])        dealer_profiles_list = [            {'id': profile.id, 'name': profile.user.name}            for profile in DealerProfile.objects.filter(id__in=dealer_profiles_data)        ]        rep['products'] = ShortProductSerializer(instance.products, many=True).data        rep['dealer_profiles'] = dealer_profiles_list        return repclass MarketerProductImageSerializer(serializers.ModelSerializer):    class Meta:        model = ProductImage        fields = ('id', 'image', 'position')class MarketerProductSizeSerializer(serializers.ModelSerializer):    class Meta:        model = ProductSize        fields = '__all__'class DealerStatusSerializer(serializers.ModelSerializer):    class Meta:        model = DealerStatus        fields = '__all__'class StoryListSerializer(serializers.ModelSerializer):    class Meta:        model = Story        fields = '__all__'class StoryDetailSerializer(serializers.ModelSerializer):    class Meta:        model = Story        fields = '__all__'    def to_representation(self, instance):        rep = super(StoryDetailSerializer, self).to_representation(instance)        dealer_profiles_data = rep.get('dealer_profiles', [])        dealer_profiles_list = [            {'id': profile.id, 'name': profile.user.name}            for profile in DealerProfile.objects.filter(id__in=dealer_profiles_data)        ]        rep['products'] = ShortProductSerializer(instance.products, many=True).data        rep['dealer_profiles'] = dealer_profiles_list        return repclass CRMNotificationSerializer(serializers.ModelSerializer):    class Meta:        model = CRMNotification        fields = '__all__'    def create(self, validated_data):        notifications_to_create = []        dealer_profiles = validated_data['dealer_profiles']        dealer_profile_ids = [dealer_profile.id if isinstance(dealer_profile, DealerProfile) else dealer_profile for                              dealer_profile in dealer_profiles]        users = MyUser.objects.filter(dealer_profile__id__in=dealer_profile_ids)        instance = super(CRMNotificationSerializer, self).create(validated_data)        for user in users:            notification_data = {                'user': user,                'notification': instance,                'title': validated_data.get('title'),                'description': validated_data.get('description'),                'status': validated_data.get('status'),                'link_id': validated_data.get('link_id')            }            notifications_to_create.append(notification_data)        if instance.image:            image_full_url = str(instance.image.url).split('/')[-2:]            image_url = '/'.join(image_full_url)        else:            image_url = None        dispatch_date = instance.dispatch_date        create_notifications(notifications_to_create, image_url=image_url, dispatch_date=dispatch_date)        return instance    def to_representation(self, instance):        representation = super(CRMNotificationSerializer, self).to_representation(instance)        dealer_profiles_data = representation.get('dealer_profiles', [])        dealer_profiles_list = [            {'id': profile.id, 'name': profile.user.name}            for profile in DealerProfile.objects.filter(id__in=dealer_profiles_data)        ]        representation['dealer_profiles'] = dealer_profiles_list        return representationclass MotivationSerializer(serializers.ModelSerializer):    class Meta:        model = Motivation        fields = ('id', 'title')class DiscountSerializer(serializers.ModelSerializer):    class Meta:        model = Discount        fields = ('id', 'title')class MarketerTaskFileSerializer(serializers.ModelSerializer):    class Meta:        model = CRMTaskFile        fields = ('id', 'file')class MarketerTaskSerializer(serializers.ModelSerializer):    files = MarketerTaskFileSerializer(many=True, read_only=True)    class Meta:        model = CRMTask        fields = ('id', 'title', 'text', 'end_date', 'created_at', 'files')class MarketerCRMTaskResponseFileSerializer(serializers.ModelSerializer):    class Meta:        model = CRMTaskResponseFile        fields = '__all__'class MarketerCRMTaskResponseSerializer(serializers.ModelSerializer):    task = MarketerTaskSerializer(read_only=True)    files = MarketerCRMTaskResponseFileSerializer(many=True, read_only=True, source='response_files')    class Meta:        model = CRMTaskResponse        fields = '__all__'