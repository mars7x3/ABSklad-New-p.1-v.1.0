from rest_framework.permissions import BasePermission


class IsDirector(BasePermission):
    def has_permission(self, request, view):
        if request.user.status == 'director':
            return True
        return False
