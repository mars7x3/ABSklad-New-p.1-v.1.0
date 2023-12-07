from rest_framework.permissions import IsAuthenticated

from crm_manager.paginations import AppPaginationClass
from crm_manager.permissions import IsManager


class ManagerMixin:
    permission_classes = (IsAuthenticated, IsManager,)
    pagination_class = AppPaginationClass

    def get_serializer_context(self):
        context = super().get_serializer_context()
        staff_profile = self.request.user.staff_profile
        context.setdefault("city", staff_profile.city)
        context.setdefault("stock", staff_profile.stock)
        return context
