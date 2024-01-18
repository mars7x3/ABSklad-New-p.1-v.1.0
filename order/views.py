import datetime

from django.utils import timezone
from django.utils.crypto import get_random_string
from drf_yasg.utils import swagger_auto_schema

from rest_framework import status, viewsets, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from order.main_functions import purchase_analysis
from order.models import MyOrder, Cart, CartProduct, OrderReceipt
from order.serializers import MyOrderListSerializer, MyOrderDetailSerializer, MyOrderCreateSerializer, \
    CartListSerializer, CartCreateSerializer
from product.views import AppProductPaginationClass


class PurchaseAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        result_data = purchase_analysis(request)
        return Response(result_data, status=status.HTTP_200_OK)


class MyOrderListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = MyOrder.objects.all()
    serializer_class = MyOrderDetailSerializer
    pagination_class = AppProductPaginationClass

    def get_queryset(self):
        queryset = self.request.user.dealer_profile.orders.filter(is_active=True)
        return queryset

    def get_serializer_class(self):
        if self.kwargs.get('pk'):
            return MyOrderDetailSerializer
        else:
            return MyOrderListSerializer

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}
        city = request.query_params.get('city')
        o_status = request.query_params.get('status')

        if city:
            kwargs['stock__city__slug'] = city

        if o_status:
            kwargs['status'] = o_status

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
            order = MyOrder.objects.filter(id=order_id).first()
            if order:
                OrderReceipt.objects.bulk_create([OrderReceipt(order=order, file=i) for i in receipts])
                response_data = MyOrderDetailSerializer(order, context=self.get_renderer_context()).data
                return Response(response_data, status=status.HTTP_200_OK)
            return Response({'text': 'По такому id заказ осутсвует!'}, status=status.HTTP_400_BAD_REQUEST)
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

            for c in carts:
                cart, _ = Cart.objects.get_or_create(dealer=dealer, stock_id=c.get('stock'))
                cart.cart_products.all().delete()
                cart_product_list = [CartProduct(cart=cart, product_id=p.get('id'), count=p.get('count')) for p in
                                     c.get('products')]
                CartProduct.objects.bulk_create(cart_product_list)
                if not cart.cart_products.exists():
                    cart.delete()
            return Response({"text": "Success!"}, status=status.HTTP_200_OK)
        else:
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)





