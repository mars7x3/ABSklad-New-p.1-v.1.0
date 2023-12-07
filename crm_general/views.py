from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from account.models import MyUser
from crm_general.serializers import StaffListSerializer


class StaffListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = MyUser.objects.exclude(status__in=['dealer', 'dealer_1c'])
    serializer_class = StaffListSerializer



