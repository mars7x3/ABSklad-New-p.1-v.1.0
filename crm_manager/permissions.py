from rest_framework.permissions import BasePermission


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_manager and getattr(request.user, 'staff_profile', None
                                                                    )
