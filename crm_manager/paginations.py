from rest_framework.pagination import PageNumberPagination


class CategoryPagination(PageNumberPagination):
    page_size = 30
    max_page_size = 40


class ProductPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 30


class ProfilePagination(PageNumberPagination):
    page_size = 20
    max_page_size = 40


class OrderPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 40
