from rest_framework.permissions import BasePermission


class IsRop(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_rop and hasattr(request.user, 'rop_profile')

