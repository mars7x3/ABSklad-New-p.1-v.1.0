
from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated

from promotion.models import Story
from promotion.serializers import StoryListSerializer, StoryDetailSerializer


class StoriesListView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Story.objects.filter(is_active=True)

    def get_serializer_class(self):
        if self.action == 'list':
            return StoryListSerializer
        else:
            return StoryDetailSerializer





