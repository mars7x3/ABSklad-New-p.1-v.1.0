from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, Sum, F
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, CreateModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet, ModelViewSet
from rest_framework.permissions import IsAuthenticated

from account.models import MyUser
from one_c.models import MovementProducts
from order.db_request import query_debugger
from order.models import MyOrder, OrderProduct, ReturnOrderProduct, ReturnOrder, ReturnOrderProductFile
from product.models import AsiaProduct, Collection, Category, ProductCount
from .permissions import IsWareHouseManager
from crm_general.paginations import GeneralPurposePagination, ProductPagination
from .serializers import OrderListSerializer, OrderDetailSerializer, WareHouseProductListSerializer, \
    WareHouseCollectionListSerializer, WareHouseCategoryListSerializer, \
    WareHouseProductSerializer, WareHouseInventorySerializer, \
    InventoryProductListSerializer, ReturnOrderProductSerializer, ReturnOrderSerializer
from .mixins import WareHouseManagerMixin
from ..models import Inventory, CRMTask
from ..tasks import minus_quantity


class WareHouseOrderView(WareHouseManagerMixin, ReadOnlyModelViewSet):
    queryset = MyOrder.objects.all()
    permission_classes = [IsAuthenticated, IsWareHouseManager]
    pagination_class = GeneralPurposePagination
    serializer_class = OrderListSerializer
    retrieve_serializer_class = OrderDetailSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        order_status = self.request.query_params.get('status')
        type_status = self.request.query_params.get('type_status')
        start_time = self.request.query_params.get('start_time')
        end_time = self.request.query_params.get('end_time')
        search = self.request.query_params.get('search')

        if order_status:
            queryset = queryset.filter(status=order_status)
        if type_status:
            queryset = queryset.filter(type_status=type_status)

        if start_time and end_time:
            queryset = queryset.filter(created_at__gte=start_time, created_at__lte=end_time)

        if search:
            queryset = queryset.filter(Q(name__icontains=search), Q(gmail__icontains=search))

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
        order_status = self.request.data.get('status')
        order_id = self.request.data.get('order_id')
        try:
            order = MyOrder.objects.get(id=order_id)
        except ObjectDoesNotExist:
            return Response({'detail': 'order_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        if order_status == 'paid':
            if order.type_status == 'cash':
                order.status = 'paid'
                order.save()
                return Response({'detail': 'Order type status successfully changed to "paid"'},
                                status=status.HTTP_200_OK)
            return Response({'detail': 'Order type status must be "cash" to change to "paid"'},
                            status=status.HTTP_400_BAD_REQUEST)

        if order_status == 'sent':
            if order.status == 'paid':
                order.status = 'sent'
                order.save()
                minus_quantity(order.id, self.request.user.warehouse_profile.stock.id)
                return Response({'detail': 'Order status successfully changed to "sent"'},
                                status=status.HTTP_200_OK)
            return Response({'detail': 'Order status must be "paid" to change to "sent"'},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Incorrect order status'}, status=status.HTTP_400_BAD_REQUEST)


class WareHouseProductViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = AsiaProduct.objects.all()
    serializer_class = WareHouseProductListSerializer
    retrieve_serializer_class = WareHouseProductSerializer
    permission_classes = [IsAuthenticated, IsWareHouseManager]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        product_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        if product_status == 'active':
            queryset = queryset.filter(is_active=True)
        elif product_status == 'inactive':
            queryset = queryset.filter(is_active=False)

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
        queryset = self.queryset
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

            statistics_entry = {
                "id": product.id,
                "vendor_code": product.vendor_code,
                "title": product.title,
                "category": product.category.title,
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
                             GenericViewSet):
    permission_classes = [IsAuthenticated, IsWareHouseManager]
    serializer_class = WareHouseInventorySerializer
    pagination_class = GeneralPurposePagination

    def get_queryset(self):
        return (Inventory.objects.filter(products__product__counts__stock=self.request.user.warehouse_profile.stock)
                .distinct())

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
        category_id = self.request.query_params.get('category_id')
        search = self.request.query_params.get('search')
        products = AsiaProduct.objects.filter(category__id=category_id)
        if search:
            products = products.filter(title__icontains=search)
        serializer = InventoryProductListSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReturnOrderProductView(ListModelMixin,
                             RetrieveModelMixin,
                             CreateModelMixin,
                             GenericViewSet):
    queryset = ReturnOrder.objects.all()
    permission_classes = [IsAuthenticated, IsWareHouseManager]
    serializer_class = ReturnOrderSerializer


class ReturnOrderProductFileAPIView(APIView):
    def post(self, request, *args, **kwargs):
        request_body = self.request.data
        return_product_id = request_body.get('return_product_id')
        return_product = ReturnOrderProduct.objects.get(id=return_product_id)
        files = self.request.FILES.getlist('files')

        files_to_create = []
        for file in files:
            files_to_create.append(
                ReturnOrderProductFile(
                    return_product=return_product,
                    file=file
                )
            )
        ReturnOrderProductFile.objects.bulk_create(files_to_create)
        return Response({'detail': 'Success'}, status=status.HTTP_201_CREATED)

