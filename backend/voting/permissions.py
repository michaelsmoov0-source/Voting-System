from django.conf import settings
from django.utils import timezone
from rest_framework.permissions import BasePermission

from .models import AdminMFA


class HasAdminAPIKey(BasePermission):
    message = "Invalid or missing admin API key."

    def has_permission(self, request, view):
        if not settings.ADMIN_API_KEY:
            return False
        return request.headers.get("X-Admin-Key") == settings.ADMIN_API_KEY


class IsAdminUserOrAPIKey(BasePermission):
    message = "Admin authentication required."

    def has_permission(self, request, view):
        user = request.user
        if user and user.is_authenticated and user.is_staff:
            try:
                profile = AdminMFA.objects.get(user=user, is_enabled=True)
            except AdminMFA.DoesNotExist:
                self.message = "Admin MFA is not configured."
                return False
            if not profile.last_verified_at:
                self.message = "Admin MFA verification required."
                return False
            # MFA must be verified for every admin session
            return True
        if settings.ADMIN_API_KEY and request.headers.get("X-Admin-Key") == settings.ADMIN_API_KEY:
            return True
        return False
