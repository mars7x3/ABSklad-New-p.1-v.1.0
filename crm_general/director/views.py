from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from account.models import MyUser, Wallet
from crm_general.director.permissions import IsDirector
from crm_general.director.serializers import StaffCRUDSerializer, BalanceListSerializer
from general_service.models import Stock
from crm_general.views import CRMPaginationClass
from order.db_request import query_debugger
from product.models import ProductPrice


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
            kwargs['staff_profile__name__icontains'] = name
        if status:
            kwargs['status'] = u_status
        if is_active:
            kwargs['is_active'] = bool(int(is_active))

        queryset = queryset.filter(**kwargs)
        response_data = self.get_serializer(queryset, many=True, context=self.get_renderer_context()).data
        return Response(response_data, status=status.HTTP_200_OK)


class BalanceListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = Wallet.objects.all()
    serializer_class = BalanceListSerializer


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
