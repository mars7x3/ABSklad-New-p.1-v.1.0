from rest_framework.generics import CreateAPIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import BasePermission, IsAuthenticated

from chat.serializers import MessageSerializer


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_manager


class IsManagerOrDealer(IsManager):
    def has_permission(self, request, view):
        return super().has_permission(request, view) or request.user.is_dealer


class MessageCreateAPIView(CreateAPIView):
    permission_classes = (IsAuthenticated, IsManagerOrDealer)
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    serializer_class = MessageSerializer
