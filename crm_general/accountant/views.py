import datetime

from django.db.models import Case, When
from django.utils import timezone
from rest_framework import viewsets, status, mixins, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from crm_general.accountant.permissions import IsAccountant
from order.models import MyOrder


class AccountantOrderListView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsAccountant]
    queryset = MyOrder.objects.all()
    serializer_class = DirectorTaskListSerializer