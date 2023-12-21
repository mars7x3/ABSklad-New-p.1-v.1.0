from rest_framework.permissions import BasePermission


class IsMarketer(BasePermission):
    def has_permission(self, request, view):
        if request.user.status == 'marketer':
            return True
        return False
