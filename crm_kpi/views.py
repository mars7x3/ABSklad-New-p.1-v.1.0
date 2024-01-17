import datetime

from django.db.models import Sum, F
from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.models import ManagerProfile, MyUser
from crm_general.director.permissions import IsDirector
from crm_kpi.models import DealerKPIProduct, DealerKPI
from crm_kpi.paginations import DealerKPIPagination
from crm_kpi.serializers import DealerKPISerializer, DealerListSerializer, ProductListKPISerializer, \
    DealerKPIDetailSerializer, DealerKPIProductSerializer, DealerKPITMZTotalSerializer
from crm_kpi.utils import kpi_total_info, kpi_main_2lvl
from product.models import AsiaProduct


class ManagerKPITMZView(APIView):
    def get(self, request, *args, **kwargs):
        managers = ManagerProfile.objects.all()  # TODO: filter managers by is_main=True
        data = []
        for manager in managers:
            total_tmz_count = DealerKPIProduct.objects.filter(
                kpi__user__dealer_profile__managers__manager_profile=manager).aggregate(
                total_count_sum=Sum('count')
            )
            data.append({
                'manager_id': manager.user.id,
                'manager': manager.user.name,
                'total_count': total_tmz_count['total_count_sum']
            })
        return Response(data)


class ManagerKPIPDSListView(APIView):
    def get(self, request, *args, **kwargs):
        managers = ManagerProfile.objects.all()  # TODO: filter managers by is_main=True
        data = []
        for manager in managers:
            total_pds = DealerKPI.objects.filter(
                user__dealer_profile__managers__manager_profile=manager).aggregate(
                total_pds_sum=Sum('pds')
            )

            data.append({
                'manager_id': manager.user.id,
                'manager': manager.user.name,
                'total_pds_sum': total_pds['total_pds_sum']
            })
        return Response(data)


class ManagerKPIPDSDetailView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def get(self, request, *args, **kwargs):
        manager_id = self.request.query_params.get('manager_id')
        if manager_id is None:
            return Response({'detail': 'manager_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        kpis = DealerKPI.objects.filter(user__dealer_profile__managers__manager_profile__user__id=manager_id)

        paginator = DealerKPIPagination()
        page = paginator.paginate_queryset(kpis, request)
        serializer = DealerKPISerializer(page, many=True).data
        return paginator.get_paginated_response(serializer)


class ManagerKPITMZDetailView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def get(self, request, *args, **kwargs):
        manager_id = self.request.query_params.get('manager_id')
        if manager_id is None:
            return Response({'detail': 'manager_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        user_total_counts = DealerKPIProduct.objects.filter(
            kpi__user__dealer_profile__managers__manager_profile__user__id=manager_id
        ).values(
            'kpi__user__id'
        ).annotate(
            user__name=F('kpi__user__name'),
            total_count=Sum('count'),
            total_fact_count=F('fact_count')
        )
        paginator = DealerKPIPagination()
        page = paginator.paginate_queryset(user_total_counts, request)
        serializer = DealerKPITMZTotalSerializer(page, many=True).data
        return paginator.get_paginated_response(serializer)


class DealerKPIView(viewsets.ModelViewSet):
    queryset = DealerKPI.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = DealerKPISerializer
    retrieve_serializer_class = DealerKPIDetailSerializer

    def get_serializer_class(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class

    def list(self, request, *args, **kwargs):
        today = timezone.now()
        current_month = today.month

        request_query = self.request.query_params
        month = request_query.get('month')
        if month:
            queryset = self.queryset.filter(month__month=month)
        else:
            queryset = self.queryset.filter(month__month=current_month)

        search = request_query.get('search')
        if search:
            queryset = queryset.filter(user__name__icontains=search)

        paginator = DealerKPIPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = DealerKPISerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(methods=['GET'], detail=False, url_path='dealers')
    def get_dealers_for_kpi(self, request, *args, **kwargs):
        search = self.request.query_params.get('search')
        dealers = MyUser.objects.filter(is_active=True, status='dealer')

        if search:
            dealers = dealers.filter(name__icontains=search)

        serializer = DealerListSerializer(dealers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False, url_path='products')
    def get_product_for_kpi(self, request, *args, **kwargs):
        search = self.request.query_params.get('search')
        products = AsiaProduct.objects.filter(is_active=True)

        if search:
            products = products.filter(title__icontains=search)
        else:
            return Response({'detail': 'search required!'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ProductListKPISerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class KPITotalView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def get(self, request):
        month = request.query_params.get('month')
        month = timezone.make_aware(datetime.datetime.strptime(month, "%m-%Y")).month

        return Response(kpi_total_info(month), status=status.HTTP_200_OK)


class KPITotalMain2lvlView(APIView):
    permission_classes = [IsAuthenticated, IsDirector]

    def get(self, request):
        month = request.query_params.get('month')
        stat_type = request.query_params.get('stat_type')

        month = timezone.make_aware(datetime.datetime.strptime(month, "%m-%Y")).month

        return Response({'result': kpi_main_2lvl(month, stat_type)}, status=status.HTTP_200_OK)

