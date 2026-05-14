from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied, Throttled
from api_management.models import APICallQuota


class IsAPIKeyAuthenticated(BasePermission):
    """
    Allows only requests authenticated via a valid API Key.
    """
    message = "A valid API key is required. Use: Authorization: Api-Key sk-..."

    def has_permission(self, request, view):
        # request.auth is the PublicAPIKey object if authentication is successful
        return (
            request.user is not None
            and request.user.is_authenticated
            and request.auth is not None
        )


class HasSufficientQuota(BasePermission):
    """
    Checks that the user has the necessary monthly quota.
    Must be used AFTER IsAPIKeyAuthenticated.

    Usage in the view :
        permission_classes = [IsAPIKeyAuthenticated, HasSufficientQuota]

    The view must define `self.get_api_quota_cost()` or leave the default as 1.
    """
    message = "Monthly quota exceeded."

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            # Reads do not consume quota
            return True

        cost = getattr(view, "quota_cost", 1)
        quota = APICallQuota.get_or_create_for_user(request.user)

        if not quota.has_sufficient_quota(cost):
            raise PermissionDenied(
                detail=(
                    f"Monthly quota exceeded. "
                    f"{quota.remaining_calls} credits remaining "
                    f"out of {quota.monthly_limit}."
                )
            )

        # Attach the quota to the request for incrementing after success
        request._quota = quota
        return True