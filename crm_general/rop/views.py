from rest_framework import views, viewsets
from rest_framework.filters import SearchFilter, OrderingFilter

from account.models import ManagerProfile
from crm_general.paginations import ProfilePagination
from .filters import ManagerFilter

from .mixins import RopMixin
from .serializers import RopManagerSerializer


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
