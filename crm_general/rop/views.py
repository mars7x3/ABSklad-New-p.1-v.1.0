from rest_framework import viewsets, generics
from rest_framework.filters import SearchFilter, OrderingFilter

from account.models import ManagerProfile
from general_service.models import Stock

from product.models import Category

from crm_general.filters import ActiveFilter
from crm_general.paginations import ProfilePagination
from crm_general.serializers import CRMCategorySerializer, CRMStockSerializer

from .filters import ManagerFilter
from .mixins import RopMixin
from .serializers import RopManagerSerializer


class ManagerStockView(RopMixin, generics.ListAPIView):
    queryset = Stock.objects.all()
    serializer_class = CRMStockSerializer
    filter_backends = (ActiveFilter, SearchFilter)
    search_fields = ("address",)

    def get_queryset(self):
        return self.queryset.filter(city=self.manager_profile.city)


class ManagerRopViewSet(RopMixin, viewsets.ModelViewSet):
    queryset = ManagerProfile.objects.select_related("user", "city").all()
    serializer_class = RopManagerSerializer
    pagination_class = ProfilePagination
    filter_backends = (SearchFilter, OrderingFilter, ManagerFilter)
    search_fields = ("user__name",)
    ordering_fields = ("user__name", "user__date_joined")
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'

    def get_queryset(self):
        return super().get_queryset().filter(city__in=self.rop_profile.cities)


class CategoryRopView(RopMixin, generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CRMCategorySerializer
    filter_backends = (SearchFilter,)
    search_fields = ("title", "slug")

