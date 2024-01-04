from rest_framework.permissions import BasePermission


class IsMainDirector(BasePermission):
    def has_permission(self, request, view):
        if request.user.status == 'main_director':
            return True
        return False
