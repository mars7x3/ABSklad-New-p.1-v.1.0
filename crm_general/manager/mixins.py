from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import get_object_or_404

from account.models import DealerProfile
from order.models import MyOrder

from .permissions import IsManager


class BaseOrderMixin:
    permission_classes = (IsAuthenticated, IsManager)
    queryset = MyOrder.objects.all()

    @property
    def manager_profile(self):
        return self.request.user.manager_profile

    def get_queryset(self):
        return super().get_queryset().filter(author__city=self.manager_profile.city)


class BaseDealerViewMixin:
    queryset = DealerProfile.objects.all()
    permission_classes = (IsAuthenticated, IsManager)

    @property
    def manager_profile(self):
        return self.request.user.manager_profile

    def get_queryset(self):
        return super().get_queryset().filter(city=self.manager_profile.city)


class BaseDealerRelationViewMixin:
    permission_classes = (IsAuthenticated, IsManager)
    lookup_field = "user_id"
    lookup_url_kwarg = "user_id"

    @property
    def manager_profile(self):
        return self.request.user.manager_profile

    def get_dealers_queryset(self):
        return DealerProfile.objects.filter(city=self.manager_profile.city)

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


class BaseManagerMixin:
    permission_classes = (IsAuthenticated, IsManager)

    @property
    def manager_profile(self):
        return self.request.user.manager_profile
