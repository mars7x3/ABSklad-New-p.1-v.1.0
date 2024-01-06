import datetime

from django.db import transaction
from django.db.models import Case, When
from django.utils import timezone
from rest_framework.filters import SearchFilter
from rest_framework import viewsets, status, mixins, generics, filters
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from account.models import MyUser, StaffMagazine
from crm_general.hr.permissions import IsHR
from crm_general.hr.serializers import HRStaffListSerializer, HRStaffDetailSerializer, HRStaffMagazineSerializer
from crm_general.views import CRMPaginationClass


class HRStaffListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsHR]
    queryset = MyUser.objects.filter(
        status__in=['director', 'main_director', 'rop', 'manager', 'marketer', 'accountant', 'warehouse', 'hr'])
    serializer_class = HRStaffListSerializer
    pagination_class = CRMPaginationClass

    def get_serializer_class(self):
        if self.detail:
            return HRStaffDetailSerializer
        return self.serializer_class


class StaffMagazineCreateView(mixins.CreateModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsHR]
    queryset = StaffMagazine.objects.all()
    serializer_class = HRStaffMagazineSerializer
