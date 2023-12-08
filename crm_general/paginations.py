from rest_framework.pagination import PageNumberPagination


class ProfilePagination(PageNumberPagination):
    page_size = 20
    max_page_size = 40
    page_size_query_param = "page_size"
