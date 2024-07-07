from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, CreateModelMixin, \
    DestroyModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated

from account.utils import send_push_notification
from crm_stat.tasks import main_stat_order_sync
from one_c import sync_tasks, task_views
from one_c.from_crm import sync_order_to_1C
from one_c.models import MovementProducts
from order.models import MyOrder, OrderProduct, ReturnOrder, MainOrder
from order.utils import get_product_list, order_total_price, order_cost_price, generate_order_products, \
    validate_order_before_sending, update_main_order_status
from product.models import AsiaProduct, Collection, Category, ProductCount
from crm_general.paginations import GeneralPurposePagination
from crm_general.models import Inventory, CRMTask, InventoryProduct
from crm_general.serializers import OrderModerationSerializer
from crm_general.tasks import minus_quantity, minus_quantity_order
from .one_c_serializers import OrderPartialSentSerializer

from .permissions import IsWareHouseManager
from .serializers import MainOrderListSerializer, WareHouseProductListSerializer, \
    WareHouseCollectionListSerializer, WareHouseCategoryListSerializer, \
    WareHouseProductSerializer, WareHouseInventorySerializer, \
    InventoryProductListSerializer, ReturnOrderSerializer, InventoryProductSerializer, \
    MainOrderDetailSerializer

from .mixins import WareHouseManagerMixin
from .utils import create_validated_data, minus_count


class WareHouseMainOrderView(WareHouseManagerMixin, task_views.OneCTaskMixin, ReadOnlyModelViewSet):
    queryset = MainOrder.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated, IsWareHouseManager]
    pagination_class = GeneralPurposePagination
    serializer_class = MainOrderListSerializer
    retrieve_serializer_class = MainOrderDetailSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        order_status = self.request.query_params.get('status')
        type_status = self.request.query_params.get('type_status')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        search = self.request.query_params.get('search')

        if order_status:
            queryset = queryset.filter(status=order_status)
        if type_status:
            queryset = queryset.filter(type_status=type_status)
        if start_date and end_date:
            queryset = queryset.filter(created_at__gte=start_date, created_at__lte=end_date)

        if search:
            queryset = queryset.filter(author__user__name__icontains=search)

        paginator = GeneralPurposePagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context())
        return paginator.get_paginated_response(serializer.data)

    def get_serializer_class(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class

    def get_queryset(self):
        return self.queryset.filter(stock=self.warehouse_profile.stock)

    @action(methods=['PATCH'], detail=False, url_path='update-status')
    def update_order_status(self, request):
        serializer = OrderModerationSerializer(data=self.request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)

        cache_key = self._save_validated_data(serializer.validated_data)
        self._run_task(sync_tasks.task_order_paid_moderation, cache_key)
        return Response(status=204)

        # order_status = self.request.data.get('status')
        # order_id = self.request.data.get('order_id')
        # try:
        #     order = MainOrder.objects.get(id=order_id)
        # except ObjectDoesNotExist:
        #     return Response({'detail': 'order_id is required or order does not exist'},
        #                     status=status.HTTP_400_BAD_REQUEST)
        #
        # if order_status == 'paid':
        #     if order.type_status == 'cash':
        #         paid_at = timezone.localtime().now()
        #         order.paid_at = paid_at
        #         order.status = 'paid'
        #         order.save()
        #         sync_money_doc_to_1C(order)
        #         kwargs = {
        #             "tokens": [order.author.user.firebase_token],
        #             "title": f"Заказ #{order_id}",
        #             'text': "Ваш заказ оплачен!",
        #             'link_id': order_id,
        #             "status": "order"
        #         }
        #
        #         send_push_notification(**kwargs)  # TODO: delay() add here
        #
        #         return Response({'detail': 'Order type status successfully changed to "paid"'},
        #                         status=status.HTTP_200_OK)
        #     return Response({'detail': 'Order type status must be "cash" to change to "paid"'},
        #                     status=status.HTTP_400_BAD_REQUEST)

        # if order_status == 'sent':
        #     if order.status == 'paid':
        #         released_at = timezone.localtime().now()
        #         order.status = order_status
        #         order.released_at = released_at
        #         order.save()
        #
        #         sync_order_to_1C.delay(order.id)
        #         main_stat_order_sync(order)
        #
        #         update_data = []
        #         for p in order.order_products.all():
        #             p.is_checked = True
        #             update_data.append(p)
        #         OrderProduct.objects.bulk_update(update_data, ['is_checked'])
        #
        #         minus_quantity(order.id, self.request.user.warehouse_profile.stock.id)
        #         return Response({'detail': f'Order status successfully changed to {order_status}'},
        #
        #                         status=status.HTTP_200_OK)
        #     return Response({'detail': f'Order status must be "paid" to change to {order_status}'},
        #                     status=status.HTTP_400_BAD_REQUEST)
        #
        # return Response({'detail': 'Incorrect order status'}, status=status.HTTP_400_BAD_REQUEST)


class WareHouseProductViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = AsiaProduct.objects.all()
    serializer_class = WareHouseProductListSerializer
    retrieve_serializer_class = WareHouseProductSerializer
    permission_classes = [IsAuthenticated, IsWareHouseManager]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        product_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        category_slug = self.request.query_params.get('category_slug')
        collection_slug = self.request.query_params.get('collection_slug')
        if product_status == 'active':
            queryset = queryset.filter(is_active=True)
        elif product_status == 'inactive':
            queryset = queryset.filter(is_active=False)

        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        if collection_slug:
            queryset = queryset.filter(collection__slug=collection_slug)

        if search:
            queryset = queryset.filter(title__icontains=search)

        serializer = self.get_serializer(queryset, many=True, context=self.get_renderer_context())
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        return self.queryset.filter(counts__stock=self.request.user.warehouse_profile.stock)

    def get_serializer_class(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class


class WareHouseCollectionViewSet(ListModelMixin,
                                 RetrieveModelMixin,
                                 GenericViewSet):
    queryset = Collection.objects.all()
    permission_classes = [IsAuthenticated, IsWareHouseManager]
    serializer_class = WareHouseCollectionListSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        c_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')

        if c_status == 'active':
            queryset = queryset.filter(is_active=True)
        elif c_status == 'inactive':
            queryset = queryset.filter(is_active=False)

        if search:
            queryset = queryset.filter(title__icontains=search)

        serializer = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data
        return Response(serializer, status=status.HTTP_200_OK)


class WareHouseCategoryViewSet(ListModelMixin,
                               RetrieveModelMixin,
                               GenericViewSet):
    queryset = Category.objects.all()
    permission_classes = [IsAuthenticated, IsWareHouseManager]
    serializer_class = WareHouseCategoryListSerializer

    def get_serializer_context(self):
        if self.detail:
            return {'request': self.request, 'retrieve': True}
        return {'request': self.request}


class WareHouseSaleReportView(WareHouseManagerMixin, APIView):
    permission_classes = [IsAuthenticated, IsWareHouseManager]

    def get(self, request, *args, **kwargs):
        order_positive_statuses = ['paid', 'sent', 'wait', 'success']
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if not start_date or not end_date:
            return Response({"error": "Both start_date and end_date are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        products = AsiaProduct.objects.filter(is_active=True, counts__stock=self.request.user.warehouse_profile.stock)
        stat = []
        for product in products:
            remains = ProductCount.objects.get(product=product, stock=self.warehouse_profile.stock).count_crm

            try:
                movement_product = MovementProducts.objects.get(product=product,
                                                                movement__is_active=True,
                                                                movement__created_at__gte=start_date,
                                                                movement__created_at__lte=end_date)
                sent_products = sum(
                    movement_product.filter(movement__warehouse_recipient_uid=self.warehouse_profile.stock.uid)
                    .values_list('count'))
                received_products = sum(
                    movement_product.filter(movement__warehouse_sender_uid=self.warehouse_profile.stock.uid)
                    .values_list('count'))
                movement_delta = sent_products - received_products
            except ObjectDoesNotExist:
                movement_delta = 0

            sold = OrderProduct.objects.filter(ab_product=product,
                                               ab_product__is_active=True,
                                               order__stock=self.warehouse_profile.stock,
                                               order__status__in=order_positive_statuses,
                                               order__created_at__range=(start_date, end_date)
                                               ).aggregate(Sum('count'))['count__sum'] or 0

            count_crm = ProductCount.objects.filter(product=product,
                                                    stock=self.warehouse_profile.stock).aggregate(
                                                    count_crm=Sum('count_crm')
                                                )
            count_1c = ProductCount.objects.filter(product=product,
                                                   stock=self.warehouse_profile.stock).aggregate(
                                                   count_1c=Sum('count_1c')
                                                )

            reserved = count_1c['count_1c'] - count_crm['count_crm']
            statistics_entry = {
                "id": product.id,
                "vendor_code": product.vendor_code,
                "title": product.title,
                "reserved": reserved,
                "category": product.category.title if product.category else None,
                "before": remains + sold + movement_delta,
                "sold": sold,
                "movements": movement_delta,
                "remains": remains
            }
            stat.append(statistics_entry)
        return Response(stat, status=status.HTTP_200_OK)


class WareHouseSaleReportDetailView(WareHouseManagerMixin, APIView):
    permission_classes = [IsAuthenticated, IsWareHouseManager]

    def get(self, request, pk, *args, **kwargs):
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        product = AsiaProduct.objects.get(id=pk)
        order_products = OrderProduct.objects.filter(ab_product=pk,
                                                     order__stock=self.warehouse_profile.stock,
                                                     order__created_at__gte=start_date, order__created_at__lte=end_date,
                                                     order__status__in=['paid', 'sent', 'wait', 'success']
                                                     )
        data = {
            'id': product.id,
            'title': product.title,
            'sales': []
        }

        sale = order_products.values('order__created_at__date', 'order__author__user', 'order__author__user__username',
                                     'order__author__user__name').annotate(
            total_count=Sum('count'), total_price=Sum('total_price')
        )
        for sale_item in sale:
            data['sales'].append({
                'date': sale_item['order__created_at__date'],
                'user_id': sale_item['order__author__user'],
                'username': sale_item['order__author__user__username'],
                'name': sale_item['order__author__user__name'],
                'total_count': sale_item['total_count'],
                'total_price': sale_item['total_price']
            })

        return Response({'result': data})


class WareHouseInventoryView(ListModelMixin,
                             RetrieveModelMixin,
                             CreateModelMixin,
                             UpdateModelMixin,
                             GenericViewSet):
    permission_classes = [IsAuthenticated, IsWareHouseManager]
    serializer_class = WareHouseInventorySerializer
    pagination_class = GeneralPurposePagination

    def get_queryset(self):
        return (Inventory.objects.filter(products__product__counts__stock=self.request.user.warehouse_profile.stock,
                                         is_active=True).distinct())

    def get_serializer_context(self):
        if self.detail:
            return {'request': self.request, 'retrieve': True}
        return {'request': self.request}

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        type_status = self.request.query_params.get('status')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if type_status:
            queryset = queryset.filter(status=type_status)

        if start_date and end_date:
            queryset = queryset.filter(created_at__gte=start_date, created_at__lte=end_date)

        paginator = GeneralPurposePagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(methods=['GET'], detail=False, url_path='products')
    def get_products(self, request, *args, **kwargs):
        user = self.request.user
        if user.warehouse_profile is None:
            return Response({'detail': 'User does not have warehouse profile'})
        stock_id = user.warehouse_profile.stock.id
        products = AsiaProduct.objects.all()
        products_in_stock = []
        for product in products:
            crm_count = sum(product.counts.filter(stock_id=stock_id).values_list('count_crm', flat=True))
            ones_count = sum(product.counts.filter(stock_id=stock_id).values_list('count_1c', flat=True))
            price = product.prices.filter().first()
            total_price = price.price * crm_count if price else 0
            if crm_count != 0 or ones_count != 0 or total_price != 0:
                products_in_stock.append(product)

        serializer = InventoryProductListSerializer(products_in_stock, context={'stock_id': stock_id}, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class InventoryProductDeleteView(DestroyModelMixin, GenericViewSet):
    queryset = InventoryProduct.objects.all()
    permission_classes = [IsAuthenticated, IsWareHouseManager]
    serializer_class = InventoryProductSerializer


class ReturnOrderProductView(ListModelMixin,
                             RetrieveModelMixin,
                             CreateModelMixin,
                             GenericViewSet):
    queryset = ReturnOrder.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated, IsWareHouseManager]
    serializer_class = ReturnOrderSerializer


class WareHouseNotificationView(APIView):
    permission_classes = [IsAuthenticated, IsWareHouseManager]

    def get(self, request):
        user = self.request.user
        order_count = MyOrder.objects.filter(stock=user.warehouse_profile.stock, status='paid').count()
        inventory_count = Inventory.objects.filter(status='new').count()
        tasks_count = CRMTask.objects.filter(status='created', executors=user).count()

        data = {
            'order_count': order_count,
            'inventory_count': inventory_count,
            'tasks_count': tasks_count,
        }

        return Response(data, status=status.HTTP_200_OK)


class VerifyOrderAuthorView(APIView):
    permission_classes = [IsAuthenticated, IsWareHouseManager]
    
    def post(self, request):
        code = request.data['code']
        order_id = request.data['order_id']
        order = MainOrder.objects.filter(id=order_id).first()
        code = order.codes.filter(code=code).first()
        if code:
            code.delete()
            return Response('Success!', status=status.HTTP_200_OK)
        return Response('Неверный код!', status=status.HTTP_400_BAD_REQUEST)


class OrderPartialSentView(APIView):
    permission_classes = [IsAuthenticated, IsWareHouseManager]

    def post(self, request):
        order_id = request.data['order_id']
        products = request.data['products']
        main_order = MainOrder.objects.filter(id=order_id).first()
        validated = validate_order_before_sending(main_order, products)
        if validated:
            validated_data = create_validated_data(main_order)
            product_list = get_product_list(products)
            price = order_total_price(product_list, products, main_order.author)
            cost_price = order_cost_price(product_list, products)
            order = MyOrder.objects.create(price=price, cost_price=cost_price, **validated_data)
            products = generate_order_products(product_list, products, main_order.author)
            OrderProduct.objects.bulk_create([OrderProduct(order=order, **i) for i in products])
            minus_count(main_order, products)
            update_main_order_status(main_order)

            sync_order_to_1C.delay(order.id)
            main_stat_order_sync(order)

            update_data = []
            for p in order.order_products.all():
                p.is_checked = True
                update_data.append(p)
            OrderProduct.objects.bulk_update(update_data, ['is_checked'])

            minus_quantity_order(order.id, self.request.user.warehouse_profile.stock.id)

            kwargs = {
                "tokens": [order.author.user.firebase_token],
                "title": f"Заказ #{order_id}",
                'text': "Ваш заказ отгружен!",
                'link_id': order_id,
                "status": "order"
            }
            send_push_notification(**kwargs)  # TODO: delay() add here

            return Response('Success!', status=status.HTTP_200_OK)
        return Response('Wrong product count data for an order shipment', status=400)


class OrderPartialSentTaskView(task_views.OneCCreateTaskMixin, task_views.OneCTaskGenericAPIView):
    permission_classes = [IsAuthenticated, IsWareHouseManager]
    serializer_class = OrderPartialSentSerializer
    create_task = sync_tasks.task_order_partial_sent

    def _save_validated_data(self, data):
        data["wh_stock_id"] = self.request.user.warehouse_profile.stock.id
        return super()._save_validated_data(data)
