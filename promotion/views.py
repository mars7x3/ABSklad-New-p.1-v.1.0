from django.db.models import Sum
from rest_framework import generics, viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.models import ManagerProfile, MyUser
from promotion.models import Story, Motivation, Banner, DealerKPIProduct
from promotion.serializers import StoryListSerializer, StoryDetailSerializer, MotivationSerializer, \
    BannerListSerializer, BannerSerializer
from promotion.utils import get_motivation_data, get_kpi_info, get_kpi_products


class StoriesListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Story.objects.filter(is_active=True)

    def get_serializer_class(self):
        if self.action == 'list':
            return StoryListSerializer
        else:
            return StoryDetailSerializer


class MotivationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response_data = get_motivation_data(request.user.dealer_profile)

        return Response(response_data, status=status.HTTP_200_OK)


class BannerListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Banner.objects.filter(is_active=True)
    serializer_class = BannerListSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return BannerListSerializer
        else:
            return BannerSerializer

    def get_queryset(self):
        dealer = self.request.user.dealer_profile
        queryset = dealer.banners.filter(is_active=True)
        return queryset


class KPIInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = get_kpi_info(request.user)
        return Response(data, status=status.HTTP_200_OK)


class KPIProductsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = get_kpi_products(request.user)
        return Response(data, status=status.HTTP_200_OK)


class ManagerKPITMZView(APIView):
    def get(self, request, *args, **kwargs):
        managers = ManagerProfile.objects.filter(is_main=True)
        data = []
        for manager in managers:
            total_tmz_count = DealerKPIProduct.objects.filter(
                user__dealer_profile__managers__manager_profile=manager).values(
                'product'
            ).annotate(
                total_count=Sum('count')
            )

            data.append({
                'manager': manager.user.name,
                'total_count': total_tmz_count
            })

        return data


class ManagerKPIPDSListView(APIView):
    def get(self, request, *args, **kwargs):
        managers = ManagerProfile.objects.filter(is_main=True)
        data = []
        for manager in managers:
            total_pds = DealerKPIProduct.objects.filter(
                user__dealer_profile__managers__manager_profile=manager).values(
                'product'
            ).annotate(
                total_pds=Sum('pds')
            )

            data.append({
                'manager': manager.user.name,
                'total_count': total_pds
            })

        return data


class ManagerKPITMZDetailView(APIView):
    def get(self, request, *args, **kwargs):
        manager_id = self.request.query_params.get('manager_id')
        pass

