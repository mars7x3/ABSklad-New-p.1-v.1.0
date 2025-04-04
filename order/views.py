import datetime

from django.utils import timezone

from django.utils.crypto import get_random_string

from drf_yasg.utils import swagger_auto_schema

from rest_framework import status, viewsets, generics, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from account.utils import random_code
from order.permissions import IsAuthor
from order.main_functions import purchase_analysis
from order.models import MyOrder, Cart, CartProduct, OrderReceipt, MainOrder, MainOrderReceipt, MainOrderCode
from order.serializers import MyOrderListSerializer, MyOrderDetailSerializer, MyOrderCreateSerializer, \
    CartListSerializer, CartCreateSerializer, MainOrderCreateSerializer, MainOrderDetailSerializer, \
    MainOrderListSerializer, MainOrderUpdateSerializer
from product.views import AppProductPaginationClass


class PurchaseAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        result_data = purchase_analysis(request)
        return Response(result_data, status=status.HTTP_200_OK)


class MainOrderListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = MainOrder.objects.all()
    serializer_class = MainOrderDetailSerializer
    pagination_class = AppProductPaginationClass

    def get_queryset(self):
        queryset = self.request.user.dealer_profile.main_orders.filter(is_active=True)
        return queryset

    def get_serializer_class(self):
        if self.kwargs.get('pk'):
            return MainOrderDetailSerializer
        else:
            return MainOrderListSerializer

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}
        stock = request.query_params.get('stock')
        o_status = request.query_params.get('status')

        if stock:
            kwargs['stock_id'] = stock

        if o_status:
            kwargs['status'] = o_status

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date and end_date:
            start_date = timezone.make_aware(datetime.datetime.strptime(start_date, "%d-%m-%Y"))
            end_date = timezone.make_aware(datetime.datetime.strptime(end_date, "%d-%m-%Y"))
            end_date = end_date + datetime.timedelta(days=1)
            kwargs['created_at__gte'] = start_date
            kwargs['created_at__lte'] = end_date

        queryset = queryset.filter(**kwargs)

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context()).data
        return self.get_paginated_response(serializer)


class MyOrderCreateView(generics.CreateAPIView):
    """
    "products": {
    "product_id": product count
  },
    "type_status": "cash" ('cash', 'visa', 'wallet', 'kaspi'),
  "stock": stock id

    """
    permission_classes = [IsAuthenticated]
    queryset = MyOrder.objects.all()
    serializer_class = MyOrderCreateSerializer


class OrderReceiptAddView(APIView):
    """
    {"receipts": [file, file],
    "order_id: order_id}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        receipts = request.FILES.getlist('receipts')
        order_id = request.data.get('order_id')
        if receipts and order_id:
            order = MainOrder.objects.filter(id=order_id).first()
            if order.author.user == request.user or request.user.status == 'manager':
                if order:
                    MainOrderReceipt.objects.bulk_create([MainOrderReceipt(order=order, file=i) for i in receipts])
                    # response_data = MyOrderDetailSerializer(order, context=self.get_renderer_context()).data
                    return Response({'detail': 'Success'}, status=status.HTTP_200_OK)
                return Response({'text': 'По такому id заказ осутсвует!'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'text': 'Доступ ограничен!'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'receipts': 'Обязательное поле!',
                         'order_id': 'Обязательное поле!'
                         }, status=status.HTTP_400_BAD_REQUEST)


class CartListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dealer = request.user.dealer_profile
        carts = dealer.carts.all()
        response_data = CartListSerializer(carts, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class CartAddView(generics.GenericAPIView):
    serializer_class = CartCreateSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if serializer.is_valid():
            dealer = request.user.dealer_profile
            carts = request.data.get('carts')
            dont_delete_ids = []
            for c in carts:
                cart, _ = Cart.objects.get_or_create(dealer=dealer, stock_id=c.get('stock'))
                cart.cart_products.all().delete()
                cart_product_list = [CartProduct(cart=cart, product_id=p.get('id'), count=p.get('count')) for p in
                                     c.get('products')]
                CartProduct.objects.bulk_create(cart_product_list)
                dont_delete_ids.append(cart.id)

            request.user.dealer_profile.carts.exclude(id__in=dont_delete_ids).delete()
            return Response({"text": "Success!"}, status=status.HTTP_200_OK)
        else:
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MainOrderCreateView(mixins.CreateModelMixin,
                          mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin,
                          GenericViewSet):
    """
    "products": {
    "product_id": product count
  },
    "type_status": "cash" ('cash', 'visa', 'wallet', 'kaspi'),
    "stock": stock id
    """
    permission_classes = [IsAuthenticated, IsAuthor]
    queryset = MainOrder.objects.all()
    serializer_class = MainOrderCreateSerializer


class MainOrderReceiptAddView(APIView):
    """
    {"receipts": [file, file],
    "order_id: order_id},
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        receipts = request.FILES.getlist('receipts')
        order_id = request.data.get('order_id')

        if receipts and order_id:
            order = MainOrder.objects.filter(id=order_id).first()
            if order:
                if order.author.user == request.user or request.user.status == 'manager':
                    MainOrderReceipt.objects.bulk_create([MainOrderReceipt(order=order, file=i) for i in receipts])
                    response_data = MainOrderDetailSerializer(order, context=self.get_renderer_context()).data
                    return Response(response_data, status=status.HTTP_200_OK)
                return Response({'text': 'Доступ ограничен!'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'text': 'По такому id заказ осутсвует!'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'receipts': 'Обязательное поле!',
                         'order_id': 'Обязательное поле!'
                         }, status=status.HTTP_400_BAD_REQUEST)


class MainOrderReceiptRemoveView(APIView):
    """
    {"remove_ids": [id, id],
    "order_id: order_id},
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id')
        remove_list = request.data.getlist('remove_ids')

        if remove_list and order_id:
            order = MainOrder.objects.filter(id=order_id).first()
            if order.author.user == request.user or request.user.status == 'manager':
                if order:
                    order.receipts.filter(id__in=remove_list).delete()
                    response_data = MainOrderDetailSerializer(order, context=self.get_renderer_context()).data
                    return Response(response_data, status=status.HTTP_200_OK)
                return Response({'text': 'По такому id заказ осутсвует!'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'text': 'Доступ ограничен!'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'receipts': 'Обязательное поле!',
                         'order_id': 'Обязательное поле!'
                         }, status=status.HTTP_400_BAD_REQUEST)


class GenerateCodeView(APIView):
    permission_classes = [IsAuthenticated]
    """"order_id: order_id}"""

    def post(self, request):
        order_id = request.data.get('order_id')
        main_order = MainOrder.objects.filter(id=order_id).first()
        if main_order.author.user == request.user:
            if main_order:
                order_code = random_code()
                MainOrderCode.objects.create(code=order_code, main_order=main_order)
                response_data = {"code": order_code}
                return Response(response_data, status=status.HTTP_200_OK)
            return Response({'text': 'По такому id заказ осутсвует!'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'text': 'Доступ ограничен!'}, status=status.HTTP_400_BAD_REQUEST)
