import datetime
from collections import OrderedDict

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, mixins, viewsets, generics
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from account.main_functions import notifications_info
from account.models import Notification, VerifyCode, DealerStore, BalancePlus, BalancePlusFile, BalanceHistory, MyUser
from account.permissions import IsAuthor, IsUserAuthor
from account.serializers import DealerMeInfoSerializer, NotificationSerializer, AccountStockSerializer, \
    DealerStoreSerializer, BalancePlusSerializer, BalanceHistorySerializer, DealerProfileUpdateSerializer, \
    UserNotificationSerializer
from account.utils import random_code, send_code_to_phone


class AppNotificationPaginationClass(PageNumberPagination):
    page_size = 1
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('total_pages', self.page.paginator.num_pages),
            ('page', self.page.number),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data),
            ('results_count', len(data)),
            ('total_results', self.page.paginator.count),
        ]))


class DealerMeInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = DealerMeInfoSerializer(request.user, context=self.get_renderer_context())

        return Response(serializer.data, status=status.HTTP_200_OK)


class DealerBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        balance = request.user.dealer_profile.wallet.amount_crm

        return Response({'balance': balance}, status=status.HTTP_200_OK)


class DealerStockInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response_data = AccountStockSerializer(request.user.dealer_profile.city.stocks.all(),
                                               context=self.get_renderer_context(), many=True).data

        return Response(response_data, status=status.HTTP_200_OK)


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        notification_id = request.data.get('notification_id')
        if notification_id:
            notification = Notification.objects.filter(id=notification_id).first()
            if notification:
                if notification.user == request.user:
                    notification.is_read = True
                    notification.save()
                    response_data = NotificationSerializer(notification, context=self.get_renderer_context()).data

                    return Response(response_data, status=status.HTTP_200_OK)
                return Response('Permission denied!', status=status.HTTP_400_BAD_REQUEST)
            return Response('Notification exist!', status=status.HTTP_400_BAD_REQUEST)
        return Response({'notification_id': 'Это поле обязательное!'}, status=status.HTTP_400_BAD_REQUEST)


class NotificationCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response_data = notifications_info(request.user)
        return Response(response_data, status=status.HTTP_200_OK)


class NotificationListView(APIView, AppNotificationPaginationClass):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifs = request.user.notifications.all()
        page = self.paginate_queryset(notifs, request)
        serializer = UserNotificationSerializer(page, many=True, context=self.get_renderer_context())
        return self.get_paginated_response(serializer.data)


class ForgotPwdView(APIView):
    """
    email
    """
    def post(self, request):
        if isinstance(request.user, AnonymousUser):
            email = request.data.get('email')
            user = get_user_model().objects.filter(email=email, is_active=True, status='dealer').first()
        else:
            email = request.user.email
            user = request.user

        if user:
            user.verify_codes.all().delete()
            verify_code = VerifyCode.objects.create(user=user, code=random_code())
            send_code_to_phone(user.phone, verify_code.code)

            return Response({'text': 'Код отправлен на телефон!'}, status=status.HTTP_200_OK)
        return Response({'text': 'Пользователь не найден!'}, status=status.HTTP_400_BAD_REQUEST)


class VerifyCodeView(APIView):
    """
    email, code
    """
    def post(self, request):
        email = request.data.get('email')
        user = get_user_model().objects.filter(email=email, is_active=True, status='dealer').first()
        if user:
            verify_code = user.verify_codes.first().code
            request_code = request.data.get('code')
            if verify_code == request_code:
                return Response({'text': 'Успешно!'}, status=status.HTTP_200_OK)
            return Response({'text': 'Неверный код!'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'text': 'Пользователь не найден!'}, status=status.HTTP_400_BAD_REQUEST)


class ChangePwdView(APIView):
    """
    email, code, pwd
    """
    def post(self, request):
        email = request.data.get('email')
        user = get_user_model().objects.filter(email=email, is_active=True, status='dealer').first()
        if user:
            verify_code = user.verify_codes.first()
            request_code = request.data.get('code')
            password = request.data.get('pwd')
            if verify_code.code == request_code:
                user.pwd = password
                user.set_password(password)
                user.save()
                # verify_code.delete()

                return Response({'text': 'Пароль успешно изменен!'}, status=status.HTTP_200_OK)
            return Response({'text': 'Неверный код!'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'text': 'Пользователь не найден!'}, status=status.HTTP_400_BAD_REQUEST)


class DealerStoreCRUDView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAuthor]
    queryset = DealerStore.objects.all()
    serializer_class = DealerStoreSerializer

    def get_queryset(self):
        queryset = self.request.user.dealer_profile.dealer_stores.all()
        return queryset


class ChangeProfileView(mixins.UpdateModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsUserAuthor]
    serializer_class = DealerProfileUpdateSerializer
    queryset = MyUser.objects.all()


class BalancePlusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = request.data.get('amount')
        files = request.FILES.getlist('files')
        dealer = request.user.dealer_profile
        if amount and files:
            # TODO: добавить синхронизацию с 1С
            balance = BalancePlus.objects.create(dealer=dealer, amount=amount)
            BalancePlusFile.objects.bulk_create([BalancePlusFile(balance=balance, file=i) for i in files])
            return Response({'text': 'Завявка принята!'}, status=status.HTTP_200_OK)
        return Response({'text': 'amount and files is required!'}, status=status.HTTP_400_BAD_REQUEST)


class BalancePlusListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = BalancePlus.objects.all()
    serializer_class = BalancePlusSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        queryset = self.request.user.dealer_profile.balances.all()
        return queryset

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        is_success = request.query_params.get('is_success')

        if start and end:
            start_date = timezone.make_aware(datetime.datetime.strptime(start, "%d-%m-%Y"))
            end_date = timezone.make_aware(datetime.datetime.strptime(end, "%d-%m-%Y"))
            end_date = end_date + timezone.timedelta(days=1)
            kwargs['created_at__gte'] = start_date
            kwargs['created_at__lte'] = end_date

        if is_success:
            kwargs['is_success'] = bool(int(is_success))

        queryset = queryset.filter(**kwargs)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True, context=self.get_renderer_context()).data
        return paginator.get_paginated_response(serializer)


class BalanceHistoryListView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    queryset = BalanceHistory.objects.filter(is_active=True)
    serializer_class = BalanceHistorySerializer
    pagination_class = AppNotificationPaginationClass

    def get_queryset(self):
        queryset = self.request.user.dealer_profile.balance_histories.all()
        return queryset

    @action(detail=False, methods=['get'])
    def search(self, request, **kwargs):
        queryset = self.get_queryset()
        kwargs = {}

        t_status = request.query_params.get('status')

        if t_status:
            kwargs['status'] = t_status
        queryset = queryset.filter(**kwargs)
        paginator = AppNotificationPaginationClass()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = BalanceHistorySerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)










