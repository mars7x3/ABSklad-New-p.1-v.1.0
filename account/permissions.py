
from rest_framework.permissions import BasePermission


class IsAuthor(BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.dealer.user == request.user:
            return True
        return False


class IsUserAuthor(BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj == request.user:
            return True
        return False
