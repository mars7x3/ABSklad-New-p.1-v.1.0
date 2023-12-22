from rest_framework.permissions import BasePermission


class IsStaff(BasePermission):
    def has_permission(self, request, view):
        if request.user.status in ['director', 'marketer', 'rop', 'manager', 'warehouse']:
            return True
        return False
