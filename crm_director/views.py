from collections import OrderedDict

from rest_framework import viewsets, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from account.models import StaffProfile, MyUser
from crm_director.permissions import IsDirector
from crm_director.serializers import StaffListSerializer, StaffCRUDSerializer


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
    queryset = MyUser.objects.exclude(status__in=['dealer', 'dealer_1'])
    serializer_class = StaffCRUDSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response({'text': 'Success!'}, status=status.HTTP_200_OK)