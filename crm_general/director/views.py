import datetime

from django.db import transaction
from django.db.models import Case, When, Q
from django.utils import timezone
from rest_framework import viewsets, status, mixins, generics, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from account.models import MyUser, Wallet, BalanceHistory, DealerStatus, DealerProfile, WarehouseProfile
from crm_general.director.permissions import IsDirector
from crm_general.director.serializers import StaffCRUDSerializer, BalanceListSerializer, BalanceHistoryListSerializer, \
    DirectorProductListSerializer, DirectorCollectionListSerializer, CollectionCategoryListSerializer, \
    CollectionCategoryProductListSerializer, DirectorProductCRUDSerializer, DirectorDiscountSerializer, \
    DirectorDiscountDealerStatusSerializer, DirectorDiscountCitySerializer, DirectorDiscountProductSerializer, \
    DirectorDealerSerializer, DirectorDealerProfileSerializer, DirectorDealerCRUDSerializer, DirDealerOrderSerializer, \
    DirDealerCartProductSerializer, DirectorMotivationCRUDSerializer, DirBalanceHistorySerializer, \
    DirectorPriceListSerializer, DirectorMotivationDealerListSerializer, DirectorTaskCRUDSerializer, \
    DirectorTaskListSerializer, DirectorMotivationListSerializer, StockListSerializer, \
    DirectorDealerListSerializer, StockProductListSerializer, DirectorStockCRUDSerializer, DirectorKPICRUDSerializer, \
    DirectorKPIListSerializer, DirectorStaffListSerializer, PriceTypeCRUDSerializer, \
    RopProfileSerializer, UserListSerializer
from crm_general.filters import FilterByFields
from crm_general.models import CRMTask, KPI

from general_service.models import Stock, City, PriceType
from crm_general.views import CRMPaginationClass
from order.db_request import query_debugger
from order.models import MyOrder, CartProduct
from product.models import ProductPrice, AsiaProduct, Collection, Category, ProductCostPrice
from promotion.models import Discount, Motivation


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

    #warehouse
    "profile_data": {
        "stock": id
    }
    """
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = MyUser.objects.filter(status__in=['rop', 'warehouse'])
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

        if u_status:
            kwargs['status'] = u_status

        if is_active:
            kwargs['is_active'] = bool(int(is_active))
        queryset = queryset.filter(**kwargs)
        response_data = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class ROPChangeView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request, *args, **kwargs):
        data = self.request.data
        deactivate_rop = data.get('deactivate_rop_id')
        new_rop = data.get('new_rop_id')
        if new_rop is None:
            return Response({'detail:', 'Can not deactivate rop without new rop for his role "new_rop_id"'},
                            status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if deactivate_rop:
                inactive_rop = MyUser.objects.get(id=deactivate_rop)
                inactive_rop.is_active = False
                inactive_rop.save()
                managers = inactive_rop.rop_profile.managers.values_list('id', flat=True)
                cities = inactive_rop.rop_profile.cities.values_list('id', flat=True)
                active_rop = MyUser.objects.get(id=new_rop)
                if managers:
                    active_rop.rop_profile.managers.add(*managers)
                    inactive_rop.rop_profile.managers.clear()
                if cities:
                    active_rop.rop_profile.cities.add(*cities)
                    inactive_rop.rop_profile.cities.clear()
                active_rop.save()

                return Response({'detail': 'Success'}, status=status.HTTP_200_OK)
            return Response({'detail', 'deactivate_rop_id required!'}, status=status.HTTP_400_BAD_REQUEST)


class WareHouseChangeView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request, *args, **kwargs):
        data = self.request.data
        deactivate_wh = data.get('deactivate_wh_id')
        new_wh = data.get('new_wh_id')
        if deactivate_wh is None:
            return Response({'detail:', 'deactivate_wh_id required!'},
                            status=status.HTTP_400_BAD_REQUEST)

        inactive_wh = MyUser.objects.get(id=deactivate_wh)

        profile = WarehouseProfile.objects.filter(user=deactivate_wh).first()
        stock = profile.stock
        wh_count = stock.warehouse_profiles.filter(user__is_active=True).count()
        if wh_count < 2:
            with transaction.atomic():
                if new_wh:
                    inactive_wh.is_active = False
                    inactive_wh.save()
                    active_wh = MyUser.objects.get(id=1965)
                    wh_profile = WarehouseProfile.objects.get(user__id=active_wh.id)
                    wh_profile.stock = stock
                    wh_profile.save()

                    return Response({'detail': 'Success'}, status=status.HTTP_200_OK)
                return Response({'detail', 'new_wh_id required!'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            inactive_wh.is_active = False
            inactive_wh.save()
            return Response({'detail': 'Success'}, status=status.HTTP_200_OK)


class BalanceListView(mixins.ListModelMixin, GenericViewSet):
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
        kwargs = {'is_active': True, 'author__user_id': user_id, 'status__in': ['success', 'sent', 'paid',
                                                                                'wait']}
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        if start_date and end_date:
            start_date = timezone.make_aware(datetime.datetime.strptime(start_date, "%d-%m-%Y"))
            end_date = timezone.make_aware(datetime.datetime.strptime(end_date, "%d-%m-%Y"))
            end_date = end_date + datetime.timedelta(days=1)
            kwargs['created_at__gte'] = start_date
            kwargs['created_at__lte'] = end_date

        amount_eco = sum(MyOrder.objects.filter(**kwargs).values_list('order_products__discount', flat=True))
        amount_crm = Wallet.objects.filter(dealer__user_id=user_id).first().amount_crm

        return Response({"amount_eco": amount_eco, "amount_crm": amount_crm}, status=status.HTTP_200_OK)


class DirectorProductListView(mixins.ListModelMixin, GenericViewSet):
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


class DirectorDiscountAsiaProductView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = AsiaProduct.objects.filter(is_active=True, is_discount=False)
    serializer_class = DirectorDiscountProductSerializer

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        discounts = Discount.objects.filter(
            Q(start_date__lte=end_date, end_date__gte=start_date) |
            Q(start_date__gte=start_date, end_date__lte=end_date) |
            Q(start_date__lte=start_date, end_date__gte=end_date))

        queryset = self.get_queryset()
        for discount in discounts:
            d_products = discount.products.all()
            queryset = queryset.exclude(id__in=d_products)

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


class DirectorDealerListView(mixins.ListModelMixin, GenericViewSet):
    """
    URL/search/?city_slug=taraz&name=nurbek&start_date=%d-%m-%Y&end_date=%d-%m-%Y
    """
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = DealerProfile.objects.all().select_related('user').prefetch_related('balance_histories')
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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = not instance.is_active
        instance.save()
        return Response({'text': 'Success!'}, status=status.HTTP_200_OK)


class DirectorBalanceHistoryListView(APIView):
    """
    {"start": "14-12-2023",
    "end": "14-12-2023",
    "user_id": user_id,
    """
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request):
        user_id = request.data.get('user_id')
        start = request.data.get('start')
        end = request.data.get('end')
        start_date = timezone.make_aware(datetime.datetime.strptime(start, "%d-%m-%Y"))
        end_date = timezone.make_aware(datetime.datetime.strptime(end, "%d-%m-%Y"))
        user = MyUser.objects.filter(id=user_id).first()
        balance_histories = user.dealer_profile.balance_histories.filter(created_at__gte=start_date,
                                                                         created_at__lte=end_date)
        response_data = DirBalanceHistorySerializer(balance_histories, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class DirectorDealerOrderListView(APIView):
    """
    {"start": "14-12-2023",
    "end": "14-12-2023",
    "user_id": user_id,
    """
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request):
        user_id = request.data.get('user_id')
        start = request.data.get('start')
        end = request.data.get('end')
        start_date = timezone.make_aware(datetime.datetime.strptime(start, "%d-%m-%Y"))
        end_date = timezone.make_aware(datetime.datetime.strptime(end, "%d-%m-%Y"))
        user = MyUser.objects.filter(id=user_id).first()
        orders = user.dealer_profile.orders.filter(created_at__gte=start_date, created_at__lte=end_date, is_active=True,
                                                   status__in=['paid', 'sent', 'wait', 'success'])
        response_data = DirDealerOrderSerializer(orders, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class DirectorDealerCartListView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request):
        user_id = request.data.get('user_id')
        user = MyUser.objects.filter(id=user_id).first()
        cart_prods = CartProduct.objects.filter(cart__in=user.dealer_profile.carts.all())
        response_data = DirDealerCartProductSerializer(cart_prods, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class DirectorTotalAmountView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request):
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        name = request.query_params.get('name')
        kwargs = {}
        if name:
            kwargs['user__name__icontains'] = name

        city_slug = request.query_params.get('city_slug')
        if city_slug:
            kwargs['city__slug'] = city_slug

        dealers = DealerProfile.objects.filter(**kwargs)
        dealer_ids = dealers.values_list('id', flat=True)
        start_date = timezone.make_aware(datetime.datetime.strptime(start_date, "%d-%m-%Y"))
        end_date = timezone.make_aware(datetime.datetime.strptime(end_date, "%d-%m-%Y"))
        balance_histories = BalanceHistory.objects.filter(is_active=True, created_at__gte=start_date,
                                                          created_at__lte=end_date, dealer_id__in=dealer_ids)
        response_data = {}
        response_data['pds_amount'] = sum(balance_histories.filter(status='wallet').values_list('amount', flat=True))
        response_data['shipment_amount'] = sum(balance_histories.filter(status='order').values_list('amount', flat=True))
        response_data['balance'] = balance_histories.last().balance if balance_histories else 0

        return Response(response_data, status=status.HTTP_200_OK)


class DirectorMotivationCRUDView(mixins.CreateModelMixin,
                                 mixins.RetrieveModelMixin,
                                 mixins.UpdateModelMixin,
                                 mixins.DestroyModelMixin,
                                 GenericViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = Motivation.objects.all()
    serializer_class = DirectorMotivationCRUDSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = not instance.is_active
        instance.save()
        return Response({'text': 'Success!'}, status=status.HTTP_200_OK)


class DirectorMotivationListView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = Motivation.objects.all()
    serializer_class = DirectorMotivationListSerializer

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


class DirectorMotivationDealerListView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = DealerProfile.objects.all()
    serializer_class = DirectorMotivationDealerListSerializer

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        kwargs = {}
        queryset = self.get_queryset()

        motivation_id = request.query_params.get('motivation')
        if motivation_id:
            motivation = Motivation.objects.filter(id=motivation_id).first()
            queryset = motivation.dealers.all()

        name = request.query_params.get('name')
        if name:
            kwargs['user__name__icontains'] = name

        city_slug = request.query_params.get('city_slug')
        if city_slug:
            kwargs['city__slug'] = city_slug

        dealer_status = request.query_params.get('dealer_status')
        if dealer_status:
            kwargs['dealer_status_id'] = dealer_status

        queryset = queryset.filter(**kwargs)
        response_data = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class DirectorPriceListView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = AsiaProduct.objects.all()
    serializer_class = DirectorPriceListSerializer

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}

        title = request.query_params.get('title')
        if title:
            kwargs['title__icontains'] = title

        category = request.query_params.get('category')
        if category:
            kwargs['category__slug'] = category

        collection = request.query_params.get('collection')
        if collection:
            kwargs['collection__slug'] = collection

        queryset = queryset.filter(**kwargs)
        response_data = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class DirectorPriceTypeCreateView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request):
        data = request.data.get('data')
        d_statuses = DealerStatus.objects.all()

        prod_ids = [i['id'] for i in data]
        cost_update_data = []
        cost_create_data = []
        price_data = []

        for d in data:
            c_price = d.get('cost_price')
            prices = d.get('prices')
            cost_price = ProductCostPrice.objects.filter(product_id=d.get('id'), is_active=True).first()
            if cost_price.price != c_price:
                cost_price.is_active = False
                cost_update_data.append(cost_price)
                cost_create_data.append(ProductCostPrice(product_id=d.get('id'), price=c_price))

            for p in prices:
                for s in d_statuses:
                    price_data.append(ProductPrice(
                        product_id=d.get('id'),
                        price_type_id=p['price_type'],
                        d_status=s,
                        price=p['price']
                    ))

        ProductCostPrice.objects.bulk_update(cost_update_data, ['is_active'])
        ProductCostPrice.objects.bulk_create(cost_create_data)
        ProductPrice.objects.filter(product_id__in=prod_ids, price_type__isnull=False).delete()
        ProductPrice.objects.bulk_create(price_data)
        return Response({'text': 'Success!'}, status=status.HTTP_200_OK)


class DirectorPriceCityCreateView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request):
        data = request.data.get('data')
        d_statuses = DealerStatus.objects.all()

        prod_ids = [i['id'] for i in data]
        cost_update_data = []
        cost_create_data = []
        price_data = []

        for d in data:
            c_price = d.get('cost_price')
            prices = d.get('prices')
            cost_price = ProductCostPrice.objects.filter(product_id=d.get('id'), is_active=True).first()
            if cost_price.price != c_price:
                cost_price.is_active = False
                cost_update_data.append(cost_price)
                cost_create_data.append(ProductCostPrice(product_id=d.get('id'), price=c_price))

            for p in prices:
                for s in d_statuses:
                    price_data.append(ProductPrice(
                        product_id=d.get('id'),
                        city_id=p['city'],
                        d_status=s,
                        price=p['price']
                    ))

        ProductCostPrice.objects.bulk_update(cost_update_data, ['is_active'])
        ProductCostPrice.objects.bulk_create(cost_create_data)
        ProductPrice.objects.filter(product_id__in=prod_ids, city__isnull=False).delete()
        ProductPrice.objects.bulk_create(price_data)
        return Response({'text': 'Success!'}, status=status.HTTP_200_OK)


class DirectorTaskCRUDView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = CRMTask.objects.all()
    serializer_class = DirectorTaskCRUDSerializer


class DirectorTaskListView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = CRMTask.objects.all()
    serializer_class = DirectorTaskListSerializer
    pagination_class = CRMPaginationClass

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}

        title = request.query_params.get('title')
        if title:
            kwargs['title__icontains'] = title

        task_status = request.query_params.get('status')
        if task_status:
            kwargs['status'] = task_status

        category = request.query_params.get('my_tasks')
        if category:
            kwargs['creator'] = request.user

        is_active = request.query_params.get('is_active')
        if is_active:
            kwargs['is_active'] = True

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date and end_date:
            start_date = timezone.make_aware(datetime.datetime.strptime(start_date, "%d-%m-%Y"))
            end_date = timezone.make_aware(datetime.datetime.strptime(end_date, "%d-%m-%Y"))
            kwargs['created_at__gte'] = start_date
            kwargs['created_at__lte'] = end_date

        queryset = queryset.filter(**kwargs)
        page = self.paginate_queryset(queryset)
        response_data = self.get_serializer(page, many=True, context=self.get_renderer_context()).data
        return self.get_paginated_response(response_data)


class DirectorStockCRUDView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = Stock.objects.select_related('city').all()
    serializer_class = DirectorStockCRUDSerializer


class DirectorStockListView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = Stock.objects.select_related('city').all()
    serializer_class = StockListSerializer

    def get_queryset(self):
        from django.db.models import F, Sum, IntegerField
        from django.db.models import OuterRef, Subquery

        return super().get_queryset().annotate(
            total_sum=Sum(
                F('counts__count_crm') * Subquery(
                    ProductPrice.objects.filter(
                        city=OuterRef('city'),
                        product_id=OuterRef('counts__product_id'),
                        d_status__discount=0
                    ).values('price')[:1]
                ), output_field=IntegerField()
            ),
            total_count=Sum('counts__count_crm'),
            norm_count=Sum('counts__count_norm'),
        )


class DStockProductListView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = AsiaProduct.objects.all()
    serializer_class = StockProductListSerializer

    def get_queryset(self):
        from django.db.models import F, Sum, IntegerField
        stock_id = self.request.query_params.get('stock')

        return super().get_queryset().annotate(
            total_count=Sum(
                Case(
                    When(counts__stock_id=stock_id, then=F('counts__count_crm')),
                    default=0,
                    output_field=IntegerField()
                )
            ),
            norm_count=Sum(
                Case(
                    When(counts__stock_id=stock_id, then=F('counts__count_norm')),
                    default=0,
                    output_field=IntegerField()
                )
            ),
        )

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


class DirectorStaffListView(mixins.RetrieveModelMixin,
                            mixins.ListModelMixin,
                            GenericViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = MyUser.objects.filter(status__in=['director', 'rop', 'manager', 'marketer', 'accountant', 'warehouse'])
    serializer_class = DirectorStaffListSerializer

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}

        name = request.query_params.get('name')
        if name:
            kwargs['name__icontains'] = name

        u_status = request.query_params.get('status')
        if u_status:
            kwargs['status'] = u_status

        city = request.query_params.get('city')
        if city:
            kwargs['manager_profile__city__slug'] = city

        queryset = queryset.filter(**kwargs)
        response_data = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False, url_path='rop-list')
    def get_active_rop_list(self, request, *args, **kwargs):
        active_rops = MyUser.objects.filter(is_active=True, status='rop')
        serializer = UserListSerializer(active_rops, many=True).data
        return Response(serializer, status=status.HTTP_200_OK)


class DirectorKPICRUDView(mixins.CreateModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin,
                          GenericViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = KPI.objects.all()
    serializer_class = DirectorKPICRUDSerializer


class DirectorKPIListView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = KPI.objects.all()
    serializer_class = DirectorKPIListSerializer
    filter_backends = (filters.SearchFilter, FilterByFields,)
    search_fields = ('executor__name',)
    filter_by_fields = {
        "status": {
            "by": "executor__status",
            "type": "string",
            "addition_schema_params": {
                "enum": [order_status for order_status, _ in MyOrder.TYPE_STATUS]
            }
        }
    }


class DirectorTaskTotalInfoView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def get(self, request):
        tasks = CRMTask.objects.filter(is_active=True)
        total_count = tasks.count()
        done_count = tasks.filter(status='completed').count()
        overdue_count = tasks.exclude(status='expired').count()
        return Response({'total_count': total_count, 'done_count': done_count, 'overdue_count': overdue_count},
                        status=status.HTTP_200_OK)


class PriceTypeCRUDView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = PriceType.objects.all()
    serializer_class = PriceTypeCRUDSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        for d in instance.dealer_profiles.all():
            d.price_type.delete()
        instance.delete()
        return Response({'text': 'Success!'}, status=status.HTTP_200_OK)


class DirFreeMainWarehouseListView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def get(self, request):
        users = MyUser.objects.filter(status='warehouse', is_active=True, warehouse_profile__stock__isnull=True)
        response_data = UserListSerializer(users, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class DirJoinWarehouseToStockListView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request):
        stock_id = request.data['stock']
        user_ids = request.data['users']
        stock = Stock.objects.get(id=stock_id)
        users = MyUser.objects.filter(id__in=user_ids)

        warehouses = WarehouseProfile.objects.filter(stock=stock)
        with transaction.atomic():
            for wh in warehouses:
                wh.stock = None
                wh.save()

            if users and stock:
                for user in users:
                    profile = user.warehouse_profile
                    profile.stock = stock
                    profile.save()
                return Response({"text": "Success!"}, status=status.HTTP_200_OK)
            return Response({"text": "stock and user not found!"}, status=status.HTTP_400_BAD_REQUEST)


class StockListView(mixins.ListModelMixin, GenericViewSet):
    queryset = Stock.objects.all().prefetch_related('counts')
    permission_classes = [IsAuthenticated, IsDirector]
    serializer_class = StockListSerializer

