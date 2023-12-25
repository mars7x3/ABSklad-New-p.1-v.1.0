from rest_framework.permissions import BasePermission


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_manager and getattr(request.user, 'manager_profile', None)


class ManagerOrderPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method == 'PATCH':
            return obj.status == 'created' or (obj.status == 'paid') and obj.type_status == 'cash'
        return False
