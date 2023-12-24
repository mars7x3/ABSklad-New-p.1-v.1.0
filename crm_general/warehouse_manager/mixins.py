from rest_framework.permissions import IsAuthenticated

from crm_general.paginations import GeneralPurposePagination
from .permissions import IsWareHouseManager


class WareHouseManagerMixin:
    permission_classes = (IsAuthenticated, IsWareHouseManager,)
    pagination_class = GeneralPurposePagination

    @property
    def warehouse_profile(self):
        return self.request.user.warehouse_profile

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.setdefault("warehouse_profile", self.warehouse_profile)
        return context
