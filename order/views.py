import datetime


from rest_framework import status, viewsets, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from order.main_functions import purchase_analysis
from order.models import MyOrder, Cart, CartProduct
from order.serializers import MyOrderListSerializer, MyOrderDetailSerializer, MyOrderCreateSerializer, \
    CartListSerializer


class PurchaseAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        result_data = purchase_analysis(request)
        return Response(result_data, status=status.HTTP_200_OK)


class MyOrderListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = MyOrder.objects.all()
    serializer_class = MyOrderDetailSerializer

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
        response_data = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class MyOrderCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = MyOrder.objects.all()
    serializer_class = MyOrderCreateSerializer


class CartListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dealer = request.user.dealer_profile
        carts = dealer.carts.all()
        response_data = CartListSerializer(carts, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class CartAddView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        dealer = request.user.dealer_profile
        carts = request.data.get('carts')

        for c in carts:
            cart, _ = Cart.objects.get_or_create(dealer=dealer, stock_id=c.get('stock'))
            cart.cart_products.delete()
            cart_product_list = [CartProduct(cart=cart, product_id=p.get('id'), count=p.get('count')) for p in
                                 c.get('products')]
            CartProduct.objects.bulk_create(cart_product_list)

        return Response({"text": "Success!"}, status=status.HTTP_200_OK)

