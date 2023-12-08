from rest_framework.permissions import IsAuthenticated

from crm_general.paginations import AppPaginationClass
from general_service.models import Stock

from .permissions import IsRop


class RopMixin:
    permission_classes = (IsAuthenticated, IsRop,)
    pagination_class = AppPaginationClass

    @property
    def rop_profile(self):
        return self.request.user.rop_profile

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.setdefault("rop_profile", self.rop_profile)
        stock_ids = Stock.objects.filter(
            city_id__in=self.rop_profile.cities.values_list("cities__id", flat=True)
        ).values_list("id", flat=True)
        context.setdefault("stock_ids", stock_ids)
        return context
