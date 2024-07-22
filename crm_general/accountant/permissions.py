from rest_framework.permissions import BasePermission


class IsAccountant(BasePermission):
    def has_permission(self, request, view):
        if request.user.status in ['accountant', 'director']:
            return True
        return False
