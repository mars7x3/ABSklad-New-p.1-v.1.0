from rest_framework.permissions import BasePermission


class IsWareHouseManager(BasePermission):
    def has_permission(self, request, view):
        if request.user.status == 'warehouse':
            return True
        return False
