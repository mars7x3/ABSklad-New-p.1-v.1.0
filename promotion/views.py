
from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated

from promotion.models import Story, Target
from promotion.serializers import StoryListSerializer, StoryDetailSerializer, TargetSerializer


class StoriesListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Story.objects.filter(is_active=True)

    def get_serializer_class(self):
        if self.action == 'list':
            return StoryListSerializer
        else:
            return StoryDetailSerializer


class TargetListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Target.objects.filter(is_active=True)
    serializer_class = TargetSerializer

    def get_queryset(self):
        queryset = self.request.user.dealer_profile.targets.filter(is_active=True)
        return queryset


