from rest_framework.permissions import BasePermission


class IsStaff(BasePermission):
    def has_permission(self, request, view):
        if request.user.status in ['director', 'marketer', 'rop', 'manager', 'warehouse', 'accountant']:
            return True
        return False
