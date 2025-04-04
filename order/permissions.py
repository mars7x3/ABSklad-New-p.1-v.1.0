
from rest_framework.permissions import BasePermission


class IsAuthor(BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.author.user == request.user:
            return True
        return False
