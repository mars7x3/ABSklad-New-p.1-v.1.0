
from rest_framework import generics, viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from promotion.models import Story, Motivation, Banner
from promotion.serializers import StoryListSerializer, StoryDetailSerializer, MotivationSerializer, BannerListSerializer
from promotion.utils import get_motivation_data


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
    queryset = Banner.objects.filter(is_active=True, status='app')
    serializer_class = BannerListSerializer

    def get_queryset(self):
        dealer = self.request.user.dealer_profile
        queryset = self.queryset.filter(cities=dealer.city, groups=dealer.dealer_status)
        return queryset


