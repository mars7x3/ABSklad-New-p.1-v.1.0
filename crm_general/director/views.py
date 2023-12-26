import datetime

from django.db.models import Case, When
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
    DirectorDealerSerializer, DirectorDealerProfileSerializer, DirectorDealerCRUDSerializer, DirDealerOrderSerializer, \
    DirDealerCartProductSerializer, DirectorMotivationCRUDSerializer, DirBalanceHistorySerializer, \
    DirectorPriceListSerializer, DirectorMotivationDealerListSerializer, DirectorTaskCRUDSerializer, \
    DirectorTaskListSerializer, DirectorMotivationListSerializer, DirectorCRMTaskGradeSerializer, StockListSerializer, \
    DirectorDealerListSerializer, StockProductListSerializer, DirectorStockCRUDSerializer, DirectorKPICRUDSerializer, \
    DirectorKPIListSerializer
from crm_general.models import CRMTask, CRMTaskResponse, CRMTaskGrade, KPI

from general_service.models import Stock, City
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

        if u_status:
            kwargs['status'] = u_status

        if is_active:
            kwargs['is_active'] = bool(int(is_active))
        print(kwargs)
        queryset = queryset.filter(**kwargs)
        response_data = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


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


class DirectorDiscountAsiaProductView(mixins.ListModelMixin, GenericViewSet):
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


class MotivationTotalView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request):
        kwargs = {}
        title = request.query_params.get('title')
        if title:
            kwargs['title__icontains'] = title

        is_active = request.query_params.get('is_active')
        if is_active:
            kwargs['is_active'] = bool(int(is_active))

        queryset = Motivation.objects.filter(**kwargs)


class MotivationTestView(APIView):
    def get(self, request):
        motivation = Motivation.objects.first()
        # data = get_motivation_dealers_stat(motivation)
        return Response('success', status=status.HTTP_200_OK)


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

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        kwargs = {}
        motivation_id = request.query_params.get('motivation')
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

        queryset = queryset.filter(**kwargs)
        response_data = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class DirectorPriceCreateView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request):
        product_id = request.data.get('id')
        c_price = request.data.get('cost_price')
        prices = request.data.get('prices')
        product = AsiaProduct.objects.filter(id=product_id).first()
        cost_price = product.cost_prices.filter(is_active=True).first()
        if cost_price.price != c_price:
            cost_price.is_active = False
            cost_price.save()
            ProductCostPrice.objects.create(product=product, price=c_price)

        d_statuses = DealerStatus.objects.all()
        price_data = []
        for p in prices:
            city = City.objects.get(id=p['city'])
            for s in d_statuses:
                price_data.append(ProductPrice(
                    product=product,
                    city=city,
                    d_status=s,
                    price=p['price']
                ))
        product.prices.all().delete()
        ProductPrice.objects.bulk_create(price_data)
        return Response({'text': 'Success!'}, status=status.HTTP_200_OK)


class DirectorTaskCRUDView(mixins.CreateModelMixin,
                           mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin,
                           mixins.DestroyModelMixin,
                           GenericViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = CRMTask.objects.all()
    serializer_class = DirectorTaskCRUDSerializer


class DirectorTaskListView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = CRMTask.objects.all()
    serializer_class = DirectorTaskListSerializer

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

        overdue = request.query_params.get('overdue')
        if overdue:
            kwargs['end_date__lte'] = timezone.now()

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date and end_date:
            start_date = timezone.make_aware(datetime.datetime.strptime(start_date, "%d-%m-%Y"))
            end_date = timezone.make_aware(datetime.datetime.strptime(end_date, "%d-%m-%Y"))
            kwargs['created_at_gte'] = start_date
            kwargs['created_at__lte'] = end_date

        queryset = queryset.filter(**kwargs)
        response_data = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class DirectorGradeCRUDView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = CRMTaskGrade.objects.all()
    serializer_class = DirectorCRMTaskGradeSerializer


class DirectorGradeView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def post(self, request):
        response_id = request.data['response_id']
        grade_id = request.data['grade_id']
        response_task = CRMTaskResponse.objects.filter(id=response_id).first()
        response_task.grade_id = grade_id
        response_task.save()
        return Response({'text': 'Success!'}, status=status.HTTP_200_OK)


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
    queryset = MyUser.objects.filter(status__in=['director', 'rop', 'manager', 'marketer', 'accountant', 'dealer',
                                                 'warehouse', 'dealer_1c', ])
    serializer_class = DirectorDealerListSerializer


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