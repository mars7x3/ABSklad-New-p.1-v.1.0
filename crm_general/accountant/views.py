import datetime

from django.db import transaction
from django.db.models import Case, When
from django.utils import timezone
from rest_framework.filters import SearchFilter
from rest_framework import viewsets, status, mixins, generics, filters
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from account.models import DealerProfile, MyUser, Wallet, BalancePlus, Notification
from crm_general.accountant.permissions import IsAccountant
from crm_general.accountant.serializers import MyOrderListSerializer, MyOrderDetailSerializer, \
    AccountantProductSerializer, AccountantCollectionSerializer, AccountantCategorySerializer, \
    AccountantStockListSerializer, AccountantStockDetailSerializer, \
    DealerProfileListSerializer, DirBalanceHistorySerializer, BalancePlusListSerializer, InventorySerializer, \
    AccountantStockShortSerializer, InventoryDetailSerializer, ReturnOrderDetailSerializer, ReturnOrderSerializer, \
    ReturnOrderProductSerializer
from crm_general.filters import FilterByFields
from crm_general.models import Inventory
from crm_general.paginations import GeneralPurposePagination

from crm_general.utils import string_date_to_date, today_on_true, convert_bool_string_to_bool
from general_service.models import Stock
from crm_general.views import CRMPaginationClass
from one_c.models import MoneyDoc
from order.models import MyOrder, ReturnOrder, ReturnOrderProduct
from crm_general.tasks import minus_quantity
from product.models import AsiaProduct, Collection, Category


class AccountantOrderListView(viewsets.ReadOnlyModelViewSet):
    # permission_classes = [IsAuthenticated, IsAccountant]
    queryset = MyOrder.objects.filter(is_active=True)
    serializer_class = MyOrderListSerializer
    pagination_class = CRMPaginationClass

    def get_serializer_class(self):
        if self.detail:
            return MyOrderDetailSerializer
        return self.serializer_class

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}

        name = request.query_params.get('name')
        if name:
            kwargs['author__user__name__icontains'] = name

        city = request.query_params.get('city')
        if city:
            kwargs['author__city__slug'] = city

        o_status = request.query_params.get('status')
        if o_status:
            kwargs['status'] = o_status

        type_status = request.query_params.get('type_status')
        if type_status:
            kwargs['type_status'] = type_status

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date and end_date:
            start_date = timezone.make_aware(datetime.datetime.strptime(start_date, "%d-%m-%Y"))
            end_date = timezone.make_aware(datetime.datetime.strptime(end_date, "%d-%m-%Y"))
            end_date = end_date + datetime.timedelta(days=1)
            kwargs['created_at__gte'] = start_date
            kwargs['created_at__lte'] = end_date

        queryset = queryset.filter(**kwargs)
        paginator = CRMPaginationClass()
        page = paginator.paginate_queryset(queryset, request)
        serializer = MyOrderListSerializer(page, many=True, context=self.get_renderer_context()).data
        return paginator.get_paginated_response(serializer)
        # serializer = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data
        # return Response(serializer, status=status.HTTP_200_OK)


class AccountantOrderTotalInfoView(APIView):
    permission_classes = [IsAuthenticated, IsAccountant]

    def get(self, request):
        orders_kwargs = {'is_active': True}
        docs_kwargs = {'is_active': True}

        name = request.query_params.get('name')
        if name:
            orders_kwargs['author__user__name__icontains'] = name
            docs_kwargs['user__name__icontains'] = name

        city = request.query_params.get('city')
        if city:
            orders_kwargs['author__city__slug'] = city
            docs_kwargs['user__dealer_profile__city__slug'] = city

        o_status = request.query_params.get('status')
        if o_status:
            orders_kwargs['status'] = o_status

        type_status = request.query_params.get('type_status')
        if type_status:
            orders_kwargs['type_status'] = type_status
            if type_status == 'visa':
                docs_kwargs['status'] = 'Без нал'
            else:
                docs_kwargs['status'] = 'Нал'

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date and end_date:
            start_date = timezone.make_aware(datetime.datetime.strptime(start_date, "%d-%m-%Y"))
            end_date = timezone.make_aware(datetime.datetime.strptime(end_date, "%d-%m-%Y"))
            end_date = end_date + datetime.timedelta(days=1)
            orders_kwargs['created_at__gte'] = start_date
            orders_kwargs['created_at__lte'] = end_date
            docs_kwargs['created_at__gte'] = start_date
            docs_kwargs['created_at__lte'] = end_date
        orders = MyOrder.objects.filter(**orders_kwargs)
        docs = MoneyDoc.objects.filter(**docs_kwargs)
        sale_sum = sum(orders.values_list('price', flat=True))
        profit_sum = sum(docs.values_list('amount', flat=True))
        response = {'sale_sum': sale_sum, 'profit_sum': profit_sum}
        return Response(response, status=status.HTTP_200_OK)


class AccountantBalanceListView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsAccountant]
    queryset = DealerProfile.objects.all()
    serializer_class = DealerProfileListSerializer
    pagination_class = CRMPaginationClass

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}

        name = request.query_params.get('name')
        if name:
            kwargs['user__name__icontains'] = name

        city = request.query_params.get('city')
        if city:
            kwargs['village__city__slug'] = city

        descending_crm = request.query_params.get('descending_crm')
        if descending_crm == 'true':
            queryset = queryset.order_by('-wallet__amount_crm')
        elif descending_crm == 'false':
            queryset = queryset.order_by('wallet__amount_crm')

        descending_1c = request.query_params.get('descending_1c')
        if descending_1c == 'true':
            queryset = queryset.order_by('-wallet__amount_1c')
        elif descending_1c == 'false':
            queryset = queryset.order_by('wallet__amount_1c')

        dealer_status = request.query_params.get('status')
        if dealer_status:
            kwargs['dealer_status'] = dealer_status

        queryset = queryset.filter(**kwargs)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context()).data

        return self.get_paginated_response(serializer)


class AccountantBalanceHistoryListView(APIView):
    """
    {"start": "14-12-2023",
    "end": "14-12-2023",
    "user_id": user_id,
    """
    permission_classes = [IsAuthenticated, IsAccountant]

    def get(self, request):
        user_id = request.query_params.get('user_id')
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        start_date = timezone.make_aware(datetime.datetime.strptime(start, "%d-%m-%Y"))
        end_date = timezone.make_aware(datetime.datetime.strptime(end, "%d-%m-%Y"))
        end_date = end_date + datetime.timedelta(days=1)

        user = MyUser.objects.filter(id=user_id).first()
        balance_histories = user.dealer_profile.balance_histories.filter(created_at__gte=start_date,
                                                                         created_at__lte=end_date)
        response_data = DirBalanceHistorySerializer(balance_histories, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class AccountantTotalEcoBalanceView(APIView):
    """
    {
    "user_id": user_id,
    "start_date": "start_date",
    "end_date": "end_date"
    }
    """
    permission_classes = [IsAuthenticated, IsAccountant]

    def get(self, request):
        user_id = request.query_params.get('user_id')
        kwargs = {'is_active': True, 'author__user_id': user_id, 'status__in': ['success', 'sent', 'paid',
                                                                                'wait']}
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if start_date and end_date:
            start_date = timezone.make_aware(datetime.datetime.strptime(start_date, "%d-%m-%Y"))
            end_date = timezone.make_aware(datetime.datetime.strptime(end_date, "%d-%m-%Y"))
            end_date = end_date + datetime.timedelta(days=1)
            kwargs['created_at__gte'] = start_date
            kwargs['created_at__lte'] = end_date

        amount_eco = sum(MyOrder.objects.filter(**kwargs).values_list('order_products__discount', flat=True))
        amount_crm = Wallet.objects.filter(dealer__user_id=user_id).first().amount_crm

        return Response({"amount_eco": amount_eco, "amount_crm": amount_crm}, status=status.HTTP_200_OK)


class BalancePlusListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsAccountant]
    queryset = BalancePlus.objects.filter(is_moderation=False)
    serializer_class = BalancePlusListSerializer

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}

        is_success = request.query_params.get('is_success')
        if is_success:
            kwargs['is_success'] = bool(int(is_success))

        queryset = queryset.filter(**kwargs)
        serializer = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data
        return Response(serializer, status=status.HTTP_200_OK)
      

class BalancePlusModerationView(APIView):
    """
    balance_id, is_success
    """
    permission_classes = [IsAuthenticated, IsAccountant]

    def post(self, request):
        balance_id = request.data.get('balance_id')
        is_success = request.data.get('is_success')
        type_status = request.data.get('type_status')

        if balance_id:
            with transaction.atomic():
                balance = BalancePlus.objects.get(is_moderation=False, id=balance_id)

                balance.is_success = is_success
                balance.is_moderation = True
                balance.save()
                if balance.is_success:
                    pass
                    # sync_balance_pay_to_1C(balance)

                return Response({'status': 'OK', 'text': 'Success!'}, status=status.HTTP_200_OK)


class AccountantOrderModerationView(APIView):
    permission_classes = [IsAuthenticated, IsAccountant]

    def post(self, request):
        order_id = request.data.get('order_id')
        order_status = request.data.get('status')

        with transaction.atomic():
            if order_id:
                if order_status in ['paid', 'rejected']:
                    order = MyOrder.objects.get(id=order_id)
                    order.status = order_status
                    order.save()
                    if order.status == 'paid':
                        minus_quantity(order.id, order.stock.id)
                        #sync_order_pay_to_1C(order)

                    kwargs = {'user': order.author.user, 'title': f'Заказ #{order.id}', 'description': order.comment,
                              'link_id': order.id, 'status': 'order'}
                    Notification.objects.create(**kwargs)

                    return Response({'status': 'OK', 'text': 'Success!'}, status=status.HTTP_200_OK)
                return Response({'status': 'Error', 'text': 'Permission denied!'}, status=status.HTTP_403_FORBIDDEN)
            return Response({'status': 'Error', 'text': 'order_id required!'}, status=status.HTTP_400_BAD_REQUEST)


class AccountantProductListView(ListModelMixin, GenericViewSet):
    queryset = AsiaProduct.objects.all()
    permission_classes = [IsAuthenticated, IsAccountant]
    serializer_class = AccountantProductSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        pr_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        if pr_status == 'active':
            queryset = queryset.filter(is_active=True)
        elif pr_status == 'inactive':
            queryset = queryset.filter(is_active=False)

        if search:
            queryset = queryset.filter(title__icontains=search)

        serializer = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data
        return Response(serializer, status=status.HTTP_200_OK)

      
class AccountantCollectionListView(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Collection.objects.all()
    permission_classes = [IsAuthenticated, IsAccountant]
    serializer_class = AccountantCollectionSerializer

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
      
      
class AccountantCategoryView(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Category.objects.all()
    permission_classes = [IsAuthenticated, IsAccountant]
    serializer_class = AccountantCategorySerializer

    def get_serializer_context(self):
        if self.detail:
            return {'request': self.request, 'retrieve': True}
        return {'request': self.request}

    def get_queryset(self):
        collection_slug = self.request.query_params.get('collection_slug')
        if collection_slug:
            return self.queryset.filter(products__collection__slug=collection_slug).distinct()
        else:
            return self.queryset
          
          
class AccountantStockViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Stock.objects.all()
    permission_classes = [IsAuthenticated, IsAccountant]
    serializer_class = AccountantStockListSerializer
    retrieve_serializer_class = AccountantStockDetailSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        stock_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        if stock_status == 'true':
            queryset = queryset.filter(is_active=True)
        elif stock_status == 'false':
            queryset = queryset.filter(is_active=False)

        if search:
            queryset = queryset.filter(city__icontains=search)

        serializer = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data
        return Response(serializer, status=status.HTTP_200_OK)

    def get_serializer_class(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class


class InventoryListUpdateView(ListModelMixin,
                              RetrieveModelMixin,
                              UpdateModelMixin,
                              GenericViewSet):

    queryset = Inventory.objects.all()
    permission_classes = [IsAuthenticated, IsAccountant]
    serializer_class = InventorySerializer
    retrieve_serializer_class = InventoryDetailSerializer
    pagination_class = GeneralPurposePagination

    def get_queryset(self):
        return Inventory.objects.all()

    def get_serializer_class(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        request_query = self.request.query_params
        stock_id = request_query.get('stock_id')
        search = request_query.get('search')
        inventory_status = request_query.get('status')

        if stock_id:
            queryset = queryset.filter(sender__warehouse_profile__stock_id=stock_id)
        if inventory_status:
            queryset = queryset.filter(status=inventory_status)
        if search:
            queryset = queryset.filter(user__name__icontains=search)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False, url_path='stock-list')
    def get_stock_list(self, request):
        stocks = Stock.objects.all()
        serializer = AccountantStockShortSerializer(stocks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReturnOrderView(ListModelMixin,
                      RetrieveModelMixin,
                      GenericViewSet):
    queryset = ReturnOrder.objects.all()
    permission_classes = [IsAuthenticated, IsAccountant]
    serializer_class = ReturnOrderSerializer
    retrieve_serializer_class = ReturnOrderDetailSerializer

    def get_queryset(self):
        search = self.request.query_params.get('search')
        order_status = self.request.query_params.get('status')
        queryset = ReturnOrder.objects.all()
        if search:
            queryset = queryset.filter(order__author__user__name__icontains=search)
        if order_status:
            queryset = queryset.filter(order__status=order_status)

        return queryset

    def get_serializer_class(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class


class ReturnOrderProductUpdateView(UpdateModelMixin, GenericViewSet):
    queryset = ReturnOrderProduct.objects.all()
    permission_classes = [IsAuthenticated, IsAccountant]
    serializer_class = ReturnOrderProductSerializer
