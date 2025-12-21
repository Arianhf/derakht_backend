from rest_framework import permissions


class IsStaffUser(permissions.BasePermission):
    """
    Custom permission to only allow staff users to access.
    """

    def has_permission(self, request, view):
        # Check if user is authenticated and is staff
        return request.user and request.user.is_authenticated and request.user.is_staff
