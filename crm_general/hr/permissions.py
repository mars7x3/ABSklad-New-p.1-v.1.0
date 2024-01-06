from rest_framework.permissions import BasePermission


class IsHR(BasePermission):
    def has_permission(self, request, view):
        if request.user.status == 'hr':
            return True
        return False
