from rest_framework.permissions import IsAuthenticated

from crm_general.paginations import AppPaginationClass

from .permissions import IsManager


class ManagerMixin:
    permission_classes = (IsAuthenticated, IsManager,)
    pagination_class = AppPaginationClass

    @property
    def manager_profile(self):
        return self.request.user.manager_profile

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.setdefault("manager_profile", self.manager_profile)
        context.setdefault("stock_ids", [self.manager_profile.stock_id])
        return context
