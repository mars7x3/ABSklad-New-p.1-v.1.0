from rest_framework.permissions import IsAuthenticated

from crm_general.paginations import AppPaginationClass

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
        return context
