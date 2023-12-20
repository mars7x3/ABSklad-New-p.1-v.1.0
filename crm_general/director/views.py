import datetime

from django.utils import timezone
from rest_framework import viewsets, status, mixins, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from account.models import MyUser, Wallet, BalanceHistory, DealerStatus, DealerProfile
from crm_general.director.permissions import IsDirector
from crm_general.director.serializers import StaffCRUDSerializer, BalanceListSerializer, BalanceHistoryListSerializer, \
    DirectorProductListSerializer, DirectorCollectionListSerializer, CollectionCategoryListSerializer, \
    CollectionCategoryProductListSerializer, DirectorProductCRUDSerializer, DirectorDiscountSerializer, \
    DirectorDiscountDealerStatusSerializer, DirectorDiscountCitySerializer, DirectorDiscountProductSerializer, \
    DirectorDealerSerializer, DirectorDealerProfileSerializer, DirectorDealerCRUDSerializer

from general_service.models import Stock, City
from crm_general.views import CRMPaginationClass
from order.db_request import query_debugger
from order.models import MyOrder
from product.models import ProductPrice, AsiaProduct, Collection, Category
from promotion.models import Discount


class StaffCRUDView(viewsets.ModelViewSet):
    """
    #rop
        "profile_data": {
            "cities": [id, id]
        }

    #manager
    "profile_data": {
        "city": id
    }

    #rop
    "profile_data": {
        "stock": id
    }
    """
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = MyUser.objects.prefetch_related('manager_profile', 'rop_profile',
                                               'warehouse_profile').filter(status__in=['rop', 'manager', 'marketer',
                                                                                       'accountant', 'warehouse',
                                                                                       'director'])
    serializer_class = StaffCRUDSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = not instance.is_active
        instance.save()
        return Response({'text': 'Success!'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}
        name = request.query_params.get('name')
        u_status = request.query_params.get('status')
        is_active = request.query_params.get('is_active')

        if name:
            kwargs['name__icontains'] = name
        if status:
            kwargs['status'] = u_status
        if is_active:
            kwargs['is_active'] = bool(int(is_active))

        queryset = queryset.filter(**kwargs)
        response_data = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class BalanceListView(generics.ListAPIView):
    """
    *QueryParams:
    {
    "name": "name",
    "city_slug": "city_slug",
    "d_status": "dealer_status_id",
    "active": 0(неактивные) / 1(активные),
    }
    """
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = Wallet.objects.all()
    serializer_class = BalanceListSerializer
    pagination_class = CRMPaginationClass

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}

        name = request.query_params.get('name')
        if name:
            kwargs['dealer__user__name__icontains'] = name

        city_slug = request.query_params.get('city_slug')
        if city_slug:
            kwargs['dealer__city__slug'] = city_slug

        d_status = request.query_params.get('d_status')
        if d_status:
            kwargs['dealer__dealer_status_id'] = d_status

        active = request.query_params.get('active')
        if active:
            if active == '1':
                kwargs['amount_1c__gte'] = 50000
            else:
                kwargs['amount_1c__lte'] = 50000

        queryset = queryset.filter(**kwargs)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context()).data

        return self.get_paginated_response(serializer)


class BalanceListTotalView(APIView):
    """
    {
    "name": "name",
    "city_slug": "city_slug",
    "d_status": "dealer_status_id",
    "active": 0(неактивные) / 1(активные),
    }
    """
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request):

        kwargs = {}
        name = request.data.get('name')
        if name:
            kwargs['dealer__user__name__icontains'] = name

        city_slug = request.data.get('city_slug')
        if city_slug:
            kwargs['dealer__city__slug'] = city_slug

        d_status = request.data.get('d_status')
        if d_status:
            kwargs['dealer__dealer_status_id'] = d_status

        active = request.data.get('active')
        if active:
            if active == 1:
                kwargs['amount_1c__gte'] = 50000
            else:
                kwargs['amount_1c__lte'] = 50000

        queryset = Wallet.objects.filter(**kwargs)
        total_crm = sum(queryset.values_list('amount_crm', flat=True))
        total_1c = sum(queryset.values_list('amount_1c', flat=True))

        return Response({"total_crm": total_crm, "total_1c": total_1c}, status=status.HTTP_200_OK)


class BalanceHistoryListView(APIView):
    """
    {
    "user_id": user_id,
    "start_date": "start_date",
    "end_date": "end_date"
    }
    """
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request):
        user_id = request.data.get('user_id')
        kwargs = {'is_active': True, 'dealer__user_id': user_id}
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        if start_date and end_date:
            start_date = timezone.make_aware(datetime.datetime.strptime(start_date, "%d-%m-%Y"))
            end_date = timezone.make_aware(datetime.datetime.strptime(end_date, "%d-%m-%Y"))
            kwargs['created_at__gte'] = start_date
            kwargs['created_at__lte'] = end_date

        queryset = BalanceHistory.objects.filter(**kwargs)
        response_data = BalanceHistoryListSerializer(queryset, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class TotalEcoBalanceView(APIView):
    """
    {
    "user_id": user_id,
    "start_date": "start_date",
    "end_date": "end_date"
    }
    """
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request):
        user_id = request.data.get('user_id')
        kwargs = {'is_active': True, 'author__user_id': user_id, 'status__in': ['Успешно', 'Отправлено', 'Оплачено',
                                                                                'Ожидание']}
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        if start_date and end_date:
            start_date = timezone.make_aware(datetime.datetime.strptime(start_date, "%d-%m-%Y"))
            end_date = timezone.make_aware(datetime.datetime.strptime(end_date, "%d-%m-%Y"))
            kwargs['created_at__gte'] = start_date
            kwargs['created_at__lte'] = end_date

        amount_eco = sum(MyOrder.objects.filter(**kwargs).values_list('order_products__discount', flat=True))
        amount_crm = Wallet.objects.filter(dealer__user_id=user_id).first().amount_crm

        return Response({"amount_eco": amount_eco, "amount_crm": amount_crm}, status=status.HTTP_200_OK)


class DirectorProductListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = AsiaProduct.objects.all().prefetch_related('prices', 'counts').select_related('category', 'collection')
    serializer_class = DirectorProductListSerializer

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}

        title = request.query_params.get('title')
        if title:
            kwargs['title__icontains'] = title

        is_active = request.query_params.get('is_active')
        if is_active:
            kwargs['is_active'] = bool(int(is_active))

        queryset = queryset.filter(**kwargs)
        response_data = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data

        return Response(response_data, status=status.HTTP_200_OK)


class DirectorCollectionListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = Collection.objects.all()
    serializer_class = DirectorCollectionListSerializer


class CollectionCategoryListView(APIView):
    """
    {
    "collection_slug": "collection_slug",
    }
    """
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request):
        collection_slug = request.data.get('collection_slug')

        queryset = Category.objects.filter(products__collection__slug=collection_slug).distinct()
        response_data = CollectionCategoryListSerializer(queryset, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class CollectionCategoryProductListView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request):
        collection_slug = request.data.get('collection_slug')
        category_slug = request.data.get('category_slug')
        products = (AsiaProduct.objects.filter(collection__slug=collection_slug, category__slug=category_slug)
                    .prefetch_related('order_products', 'prices', 'counts'))
        response_data = CollectionCategoryProductListSerializer(products, many=True,
                                                                context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class DirectorProductCRUDView(mixins.RetrieveModelMixin,
                              mixins.UpdateModelMixin,
                              mixins.DestroyModelMixin,
                              GenericViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = AsiaProduct.objects.all()
    serializer_class = DirectorProductCRUDSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = not instance.is_active
        instance.save()
        return Response({'text': 'Success!'}, status=status.HTTP_200_OK)


class DirectorDiscountCRUDView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = Discount.objects.all()
    serializer_class = DirectorDiscountSerializer

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}

        title = request.query_params.get('title')
        if title:
            kwargs['title__icontains'] = title

        is_active = request.query_params.get('is_active')
        if is_active:
            kwargs['is_active'] = bool(int(is_active))

        planned = request.query_params.get('planned')
        if planned:
            kwargs['is_active'] = True
            kwargs['start_date__gte'] = timezone.now()

        queryset = queryset.filter(**kwargs)
        response_data = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data

        return Response(response_data, status=status.HTTP_200_OK)


class DirectorDiscountAsiaProductView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = AsiaProduct.objects.filter(is_active=True, is_discount=False)
    serializer_class = DirectorDiscountProductSerializer

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}

        category = request.query_params.get('category')
        if category:
            kwargs['category__slug'] = category

        queryset = queryset.filter(**kwargs)
        response_data = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data

        return Response(response_data, status=status.HTTP_200_OK)


class DirectorDiscountCityView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = City.objects.filter(is_active=True)
    serializer_class = DirectorDiscountCitySerializer


class DirectorDiscountDealerStatusView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = DealerStatus.objects.all()
    serializer_class = DirectorDiscountDealerStatusSerializer


class DirectorDealerListView(viewsets.ReadOnlyModelViewSet):
    """
    URL/search/?city_slug=taraz&name=nurbek&start_date=%d-%m-%Y&end_date=%d-%m-%Y
    """
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = DealerProfile.objects.all().select_related('user').prefetch_related('orders', 'wallet',
                                                                                   'user__money_docs')
    serializer_class = DirectorDealerSerializer
    pagination_class = CRMPaginationClass

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}

        name = request.query_params.get('name')
        if name:
            kwargs['user__name__icontains'] = name

        city_slug = request.query_params.get('city_slug')
        if city_slug:
            kwargs['city__slug'] = city_slug

        queryset = queryset.filter(**kwargs)
        page = self.paginate_queryset(queryset)
        response_data = self.get_serializer(page, many=True, context=self.get_renderer_context()).data
        return self.get_paginated_response(response_data)


class DirectorDealerCRUDView(mixins.CreateModelMixin,
                               mixins.RetrieveModelMixin,
                               mixins.UpdateModelMixin,
                               mixins.DestroyModelMixin,
                               GenericViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = MyUser.objects.all()
    serializer_class = DirectorDealerCRUDSerializer



# class StockCRUDView(viewsets.ModelViewSet):
#     permission_classes = [IsAuthenticated, IsDirector]
#     queryset = Stock.objects.select_related('city').all()
#     serializer_class = StockCRUDSerializer
#
#     @query_debugger
#     def list(self, request, *args, **kwargs):
#         return super().list(request, *args, **kwargs)
#
#     def get_queryset(self):
#         from django.db.models import F, Sum, IntegerField
#         from django.db.models import OuterRef, Subquery
#
#         return super().get_queryset().annotate(
#             total_sum=Sum(
#                 F('counts__count_crm') * Subquery(
#                     ProductPrice.objects.filter(
#                         city=OuterRef('city'),
#                         product_id=OuterRef('counts__product_id'),
#                         d_status__discount=0
#                     ).values('price')[:1]
#                 ), output_field=IntegerField()
#             ),
#             total_count=Sum('counts__count_crm'),
#         )
#
#     def destroy(self, request, *args, **kwargs):
#         instance = self.get_object()
#         instance.is_active = not instance.is_active
#         instance.save()
#         return Response({'text': 'Success!'}, status=status.HTTP_200_OK)
