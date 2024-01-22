from rest_framework import permissions
from rest_framework.generics import get_object_or_404

from account.models import DealerProfile, ManagerProfile
from .permissions import IsRop
from .serializers import DealerProfileDetailSerializer, ManagerProfileSerializer


class BaseRopMixin:
    permission_classes = (permissions.IsAuthenticated, IsRop)

    @property
    def rop_profile(self):
        return self.request.user.rop_profile


class BaseManagerMixin:
    queryset = ManagerProfile.objects.filter(user__status="manager")
    serializer_class = ManagerProfileSerializer
    lookup_field = "user_id"
    lookup_url_kwarg = "user_id"

    @property
    def rop_profile(self):
        return self.request.user.rop_profile

    def get_queryset(self):
        return super().get_queryset().filter(city__in=self.rop_profile.cities.all())


class BaseDealerMixin:
    permission_classes = (permissions.IsAuthenticated, IsRop)
    queryset = DealerProfile.objects.filter(user__status="dealer")
    serializer_class = DealerProfileDetailSerializer
    lookup_field = "user_id"
    lookup_url_kwarg = "user_id"

    @property
    def rop_profile(self):
        return self.request.user.rop_profile

    def get_queryset(self):
        return super().get_queryset().filter(village__city__in=self.rop_profile.cities.all())


class BaseDealerRelationViewMixin:
    permission_classes = (permissions.IsAuthenticated, IsRop)
    lookup_field = "user_id"
    lookup_url_kwarg = "user_id"

    @property
    def rop_profile(self):
        return self.request.user.rop_profile

    def get_dealers_queryset(self):
        return DealerProfile.objects.filter(user__status="dealer", managers__city__in=self.rop_profile.cities.all())

    def get_dealer_profile(self) -> DealerProfile:
        queryset = self.get_dealers_queryset()

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
                'Expected view %s to be called with a URL keyword argument '
                'named "%s". Fix your URL conf, or set the `.lookup_field` '
                'attribute on the view correctly.' %
                (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj
