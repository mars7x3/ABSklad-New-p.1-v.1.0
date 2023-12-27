from rest_framework.permissions import BasePermission


class IsAccountant(BasePermission):
    def has_permission(self, request, view):
        if request.user.status == 'accountant':
            return True
        return False
