import datetime

from django.db.models import Sum, F
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import DestroyModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from account.models import ManagerProfile, MyUser
from crm_general.director.permissions import IsDirector
from crm_general.main_director.permissions import IsMainDirector
from crm_general.permissions import IsStaff
from crm_kpi.models import DealerKPIProduct, DealerKPI
from crm_kpi.paginations import DealerKPIPagination
from crm_kpi.serializers import DealerKPISerializer, DealerListSerializer, ProductListKPISerializer, \
    DealerKPIDetailSerializer, DealerKPITMZTotalSerializer, DealerKPIProductSerializer
from crm_kpi.utils import kpi_total_info, kpi_main_2lvl, kpi_main_3lvl, kpi_svd_1lvl, kpi_acb_1lvl, kpi_pds_1lvl
from product.models import AsiaProduct


class ManagerKPITMZView(APIView):
    def get(self, request, *args, **kwargs):
        managers = ManagerProfile.objects.all()  # TODO: filter managers by is_main=True
        data = []
        for manager in managers:
            total_tmz_count = DealerKPIProduct.objects.filter(
                kpi__user__dealer_profile__managers__manager_profile=manager
            ).aggregate(total_count_sum=Sum('count'))
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
                user__dealer_profile__managers__manager_profile=manager
            ).aggregate(total_pds_sum=Sum('pds'))

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
    permission_classes = [IsAuthenticated | IsDirector | IsMainDirector]
    serializer_class = DealerKPISerializer
    retrieve_serializer_class = DealerKPIDetailSerializer

    def get_serializer_class(self):
        if self.detail:
            return self.retrieve_serializer_class
        return self.serializer_class

    def list(self, request, *args, **kwargs):
        request_query = self.request.query_params
        month = request_query.get('month')
        queryset = self.get_queryset()
        if month:
            try:
                date = timezone.make_aware(datetime.datetime.strptime(month, "%m-%Y"))
            except ValueError as e:
                raise ValidationError({"detail": str(e)})

            queryset = queryset.filter(month__month=date.month, month__year=date.year)
        else:
            naive_time = timezone.localtime().now()
            today = timezone.make_aware(naive_time)
            queryset = queryset.filter(month__month=today.month, month__year=today.year)

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
        city_id = self.request.query_params.get('city_id')
        dealer_status = self.request.query_params.get('status')
        dealers = MyUser.objects.filter(is_active=True, status='dealer')
        if search:
            dealers = dealers.filter(name__icontains=search)

        if city_id:
            dealers = dealers.filter(dealer_profile__village__city_id=city_id)

        if dealer_status == 'true':
            dealers = dealers.filter(dealer_profile__wallet__amount_crm__gte=50000)
        elif dealer_status == 'false':
            dealers = dealers.filter(dealer_profile__wallet__amount_crm__lte=50000)

        paginator = DealerKPIPagination()
        page = paginator.paginate_queryset(dealers, request)
        serializer = DealerListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(methods=['GET'], detail=False, url_path='products')
    def get_product_for_kpi(self, request, *args, **kwargs):
        search = self.request.query_params.get('search')
        products = AsiaProduct.objects.filter(is_active=True)
        collection_slug = self.request.query_params.get('collection_slug')
        category_slug = self.request.query_params.get('category_slug')
        if search:
            products = products.filter(title__icontains=search)
        if collection_slug:
            products = products.filter(collection__slug=collection_slug)
        if category_slug:
            products = products.filter(category__slug=category_slug)

        serializer = ProductListKPISerializer(products, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class DeleteKPIProductView(DestroyModelMixin, GenericViewSet):
    queryset = DealerKPIProduct.objects.all()
    permission_classes = [IsAuthenticated | IsDirector | IsMainDirector]
    serializer_class = DealerKPIProductSerializer


class KPITotalView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request):
        month = request.query_params.get('month')
        if not month:
            raise ValidationError({"detail": "month is required param!"})

        try:
            date = timezone.make_aware(datetime.datetime.strptime(month, "%m-%Y"))
        except ValueError as e:
            raise ValidationError({"detail": str(e)})

        data = kpi_total_info(date)
        data |= kpi_pds_1lvl(date)
        data["svd"] = kpi_svd_1lvl(date)
        data["acb"] = kpi_acb_1lvl(date)
        return Response(data, status=status.HTTP_200_OK)


class KPITotalMain2lvlView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request):
        month = request.query_params.get('month')
        stat_type = request.query_params.get('stat_type')
        if not month or not stat_type:
            raise ValidationError({"detail": "month and stat_type required params!"})

        try:
            date = timezone.make_aware(datetime.datetime.strptime(month, "%m-%Y"))
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return Response({'result': kpi_main_2lvl(stat_type, date) or []}, status=status.HTTP_200_OK)


class KPITotalMain3lvlView(APIView):
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request, manager_id):
        month = request.query_params.get('month')
        stat_type = request.query_params.get('stat_type')

        if not month or not stat_type:
            raise ValidationError({"detail": "month and stat_type is required params!"})

        try:
            date = timezone.make_aware(datetime.datetime.strptime(month, "%m-%Y"))
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return Response(
            {'result': kpi_main_3lvl(stat_type, manager_id, date)},
            status=status.HTTP_200_OK
        )
