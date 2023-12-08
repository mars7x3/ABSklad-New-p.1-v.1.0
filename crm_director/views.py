import datetime
from collections import OrderedDict

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from account.models import StaffProfile, MyUser
from crm_director.permissions import IsDirector
from crm_director.serializers import StaffCRUDSerializer, StockCRUDSerializer
from general_service.models import Stock


class AppPaginationClass(PageNumberPagination):
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


class StaffCRUDView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsDirector]
    queryset = MyUser.objects.filter(status__in=['rop', 'manager', 'marketer', 'accountant', 'warehouse'])
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


class StockCRUDView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Stock.objects.all()
    serializer_class = StockCRUDSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = not instance.is_active
        instance.save()
        return Response({'text': 'Success!'}, status=status.HTTP_200_OK)
