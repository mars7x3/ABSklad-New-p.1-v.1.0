import datetime

from django.db.models import Sum, F, Q
from django.utils import timezone
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from account.models import DealerProfile, MyUser, Wallet, BalancePlus, Notification
from account.utils import send_push_notification
from crm_general.accountant.one_c_serializers import BalancePlusModerationSerializer
from crm_general.accountant.permissions import IsAccountant
from crm_general.accountant.serializers import MainOrderListSerializer, MainOrderDetailSerializer, \
    AccountantProductSerializer, AccountantCollectionSerializer, AccountantCategorySerializer, \
    AccountantStockListSerializer, AccountantStockDetailSerializer, \
    DealerProfileListSerializer, DirBalanceHistorySerializer, BalancePlusListSerializer, InventorySerializer, \
    AccountantStockShortSerializer, InventoryDetailSerializer, ReturnOrderDetailSerializer, ReturnOrderSerializer, \
    ReturnOrderProductSerializer
from crm_general.models import Inventory, CRMTask
from crm_general.paginations import GeneralPurposePagination
from crm_general.serializers import OrderModerationSerializer

from general_service.models import Stock
from crm_general.views import CRMPaginationClass
from one_c import task_views, sync_tasks
from one_c.from_crm import sync_1c_money_doc, sync_money_doc_to_1C
from one_c.models import MoneyDoc, MovementProduct1C
from order.models import MyOrder, ReturnOrder, ReturnOrderProduct, MainOrder
from crm_general.tasks import minus_quantity
from product.models import AsiaProduct, Collection, Category


class AccountantOrderListView(viewsets.ReadOnlyModelViewSet):
    # permission_classes = [IsAuthenticated, IsAccountant]
    queryset = MainOrder.objects.filter(is_active=True)
    serializer_class = MainOrderListSerializer
    pagination_class = CRMPaginationClass

    def get_serializer_class(self):
        if self.detail:
            return MainOrderDetailSerializer
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
        serializer = MainOrderListSerializer(page, many=True, context=self.get_renderer_context()).data
        return paginator.get_paginated_response(serializer)


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
    queryset = DealerProfile.objects.filter(Q(wallet__amount_crm__gt=0) | Q(wallet__amount_1c__gt=0))
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
        paginator = CRMPaginationClass()
        page = paginator.paginate_queryset(queryset, request)
        serializer = DealerProfileListSerializer(page, many=True, context=self.get_renderer_context()).data
        return paginator.get_paginated_response(serializer)


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
    permission_classes = [IsAuthenticated]

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
    queryset = BalancePlus.objects.all()
    serializer_class = BalancePlusListSerializer
    pagination_class = GeneralPurposePagination

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}

        is_success = request.query_params.get('is_success')
        if is_success:
            kwargs['is_success'] = bool(int(is_success))

        is_moderation = request.query_params.get('is_moderation')
        if is_moderation:
            kwargs['is_moderation'] = bool(int(is_moderation))

        name = request.query_params.get('name')
        if name:
            kwargs['author__user__name__icontains'] = name

        queryset = queryset.filter(**kwargs)
        paginator = GeneralPurposePagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context()).data
        return paginator.get_paginated_response(serializer)
      

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
            balance = BalancePlus.objects.get(is_moderation=False, id=balance_id)

            balance.is_success = is_success
            balance.is_moderation = True
            balance.save()
            kwargs = {
                "tokens": [balance.dealer.user.firebase_token],
                "title": f"Заявка на пополнение #{balance_id}",
                'link_id': balance_id,
                "status": "balance"
            }
            if balance.is_success:
                data = {
                    "status": type_status,
                    "user": balance.dealer.user,
                    "amount": balance.amount,
                    "cash_box": balance.dealer.village.city.stocks.first().cash_box
                }
                if type_status == 'cash':
                    data['status'] = 'Нал'
                elif type_status == 'visa':
                    data['status'] = 'Без нал'

                money_doc = MoneyDoc.objects.create(**data)
                sync_1c_money_doc(money_doc)

                kwargs['text'] = "Заявка на пополнение одобрено!",

            else:
                kwargs['text'] = "Заявка на пополнение отклонено.",
            send_push_notification(**kwargs)  # TODO: delay() add here

            serializer = BalancePlusListSerializer(balance, context=self.get_renderer_context())
            return Response(serializer.data, status=status.HTTP_200_OK)


class BalancePlusModerationTaskView(task_views.OneCCreateTaskMixin, task_views.OneCTaskGenericAPIView):
    permission_classes = [IsAuthenticated, IsAccountant]
    serializer_class = BalancePlusModerationSerializer
    create_task = sync_tasks.task_balance_plus_moderation


class AccountantOrderModerationView(APIView):
    permission_classes = [IsAuthenticated, IsAccountant]

    def post(self, request):
        order_id = request.data.get('order_id')
        order_status = request.data.get('status')

        if order_id:
            if order_status in ['paid', 'rejected']:
                order = MainOrder.objects.get(id=order_id)
                order.status = order_status
                order.save()
                kwargs = {
                    "tokens": [order.author.user.firebase_token],
                    "title": f"Заказ #{order_id}",
                    'link_id': order_id,
                    "status": "order"
                }
                if order_status == 'paid':
                    minus_quantity(order.id, order.stock.id)
                    sync_money_doc_to_1C(order)
                    kwargs["text"] = "Ваш заказ оплачен!",
                else:
                    kwargs["text"] = "Ваша оплата заказа не успешна.",

                send_push_notification(**kwargs)  # TODO: delay() add here

                kwargs = {'user': order.author.user, 'title': f'Заказ #{order.id}',
                          'link_id': order.id, 'status': 'order'}
                Notification.objects.create(**kwargs)

                return Response({'status': 'OK', 'text': 'Success!'}, status=status.HTTP_200_OK)

            return Response({'status': 'Error', 'text': 'Permission denied!'}, status=status.HTTP_403_FORBIDDEN)
        return Response({'status': 'Error', 'text': 'order_id required!'}, status=status.HTTP_400_BAD_REQUEST)


class AccountantOrderPaidModerationTaskView(task_views.OneCCreateTaskMixin, task_views.OneCTaskGenericAPIView):
    permission_classes = [IsAuthenticated, IsAccountant]
    serializer_class = OrderModerationSerializer
    create_task = sync_tasks.task_order_paid_moderation


class AccountantProductListView(ListModelMixin, GenericViewSet):
    queryset = AsiaProduct.objects.all()
    permission_classes = [IsAuthenticated, IsAccountant]
    serializer_class = AccountantProductSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        pr_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        collection_slug = self.request.query_params.get('collection_slug')
        category_slug = self.request.query_params.get('category_slug')
        if pr_status == 'active':
            queryset = queryset.filter(is_active=True)
        elif pr_status == 'inactive':
            queryset = queryset.filter(is_active=False)
        if collection_slug:
            queryset = queryset.filter(collection__slug=collection_slug)
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        if search:
            queryset = queryset.filter(title__icontains=search)

        serializer = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data
        return Response(serializer, status=status.HTTP_200_OK)

      
class AccountantCollectionListView(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Collection.objects.all()
    permission_classes = [IsAuthenticated, IsAccountant]
    serializer_class = AccountantCollectionSerializer

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
        instances = Category.objects.all()
        if collection_slug:
            return instances.filter(products__collection__slug=collection_slug).distinct()
        else:
            return instances
          
          
class AccountantStockViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Stock.objects.all()
    permission_classes = [IsAuthenticated, IsAccountant]
    serializer_class = AccountantStockListSerializer
    retrieve_serializer_class = AccountantStockDetailSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
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
                              task_views.OneCUpdateTaskMixin,
                              task_views.OneCTaskGenericViewSet):

    queryset = Inventory.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated, IsAccountant]
    serializer_class = InventorySerializer
    retrieve_serializer_class = InventoryDetailSerializer
    pagination_class = GeneralPurposePagination
    update_task = sync_tasks.task_inventory_update

    def _save_validated_data(self, data):
        data.pop("receiver", None)
        data["receiver_id"] = self.request.user.id
        return super()._save_validated_data(data)

    def get_serializer_class(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
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

        paginator = GeneralPurposePagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = InventorySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(methods=['GET'], detail=False, url_path='stock-list')
    def get_stock_list(self, request):
        stocks = Stock.objects.all()
        serializer = AccountantStockShortSerializer(stocks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReturnOrderView(ListModelMixin,
                      RetrieveModelMixin,
                      GenericViewSet):
    queryset = ReturnOrder.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated, IsAccountant]
    serializer_class = ReturnOrderSerializer
    retrieve_serializer_class = ReturnOrderDetailSerializer

    def get_queryset(self):
        search = self.request.query_params.get('search')
        order_status = self.request.query_params.get('status')
        queryset = ReturnOrder.objects.filter(is_active=True)
        if search:
            queryset = queryset.filter(order__author__user__name__icontains=search)
        if order_status:
            queryset = queryset.filter(order__status=order_status)

        return queryset

    def get_serializer_class(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class


class ReturnOrderProductUpdateView(task_views.OneCUpdateTaskMixin, task_views.OneCTaskGenericViewSet):
    queryset = ReturnOrderProduct.objects.all()
    permission_classes = [IsAuthenticated, IsAccountant]
    serializer_class = ReturnOrderProductSerializer
    update_task = sync_tasks.task_update_return_order


class AccountantNotificationView(APIView):
    def get(self, request):
        user = self.request.user
        inventories_count = Inventory.objects.filter(status='new').count()
        orders_count = MainOrder.objects.filter(status='created').count()
        return_orders_count = ReturnOrderProduct.objects.filter(status='created').count()
        balances_plus_count = BalancePlus.objects.filter(is_moderation=False).count()
        tasks_count = CRMTask.objects.filter(status='created', executors=user).count()

        data = {
            'inventories_count': inventories_count,
            'orders_count': orders_count,
            'return_orders_count': return_orders_count,
            'balances_plus_count': balances_plus_count,
            'tasks_count': tasks_count,
        }
        return Response(data, status=status.HTTP_200_OK)


class ProductHistoryView(APIView):
    def get(self, request, *args, **kwargs):
        query_params = self.request.query_params
        product_id = query_params.get('product_id')
        start_date = query_params.get('start_date')
        end_date = query_params.get('end_date')

        sent = MyOrder.objects.filter(is_active=True,
                                      order_products__ab_product_id=product_id,
                                      created_at__range=[start_date, end_date],
                                      status__in=['paid', 'sent', 'wait', 'success']).values(
            'created_at',
            'author'
        ).annotate(
            order_id=F('id'),
            count=Sum('order_products__count'),
            author_name=F('author__user__name'),
            stock_title=F('stock__title'),
            released_at=F('released_at'),
            total_price=F('order_products__price') * F('order_products__count')
        )

        movements = MovementProduct1C.objects.filter(is_active=True,
                                                     mv_products__product_id=product_id,
                                                     created_at__range=[start_date, end_date]).values(
            'created_at',
            'mv_products__product',
            'warehouse_recipient',
            'warehouse_sender'
        ).annotate(
            count=Sum('mv_products__count'),
            recipient_title=F('warehouse_recipient__title'),
            sender_title=F('warehouse_sender__title'),
        )

        data = {
            "sent": sent,
            "movement": movements
        }
        return Response(data)
