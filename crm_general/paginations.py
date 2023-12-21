from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ProfilePagination(PageNumberPagination):
    page_size = 20
    max_page_size = 40
    page_size_query_param = "page_size"


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


class ProductPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 40
    page_size_query_param = 'page_size'


class GeneralPurposePagination(PageNumberPagination):
    page_size = 10
    max_page_size = 40
    page_size_query_param = 'page_size'
