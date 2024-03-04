from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from account.models import MyUser
from crm_general.director.permissions import IsDirector
from crm_general.main_director.permissions import IsMainDirector
from crm_general.main_director.serializers import MainDirectorStaffCRUDSerializer, MainDirectorStockListSerializer

from general_service.models import Stock
from product.models import ProductPrice


class MainDirStaffCRUDView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsMainDirector]
    queryset = MyUser.objects.filter(status__in=['marketer', 'accountant', 'director'])
    serializer_class = MainDirectorStaffCRUDSerializer

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


class MainDirectorStockListView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsMainDirector]
    queryset = Stock.objects.select_related('city').all()
    serializer_class = MainDirectorStockListSerializer

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
