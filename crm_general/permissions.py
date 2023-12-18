from rest_framework.permissions import BasePermission


class IsStaff(BasePermission):
    def has_permission(self, request, view):
        if request.user.status in ['director']:
            return True
        return False
