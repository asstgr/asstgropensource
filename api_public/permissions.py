from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied, Throttled
from api_management.models import APICallQuota


class IsAPIKeyAuthenticated(BasePermission):
    """
    Autorise uniquement les requêtes authentifiées via une API Key valide.
    """
    message = "A valid API key is required. Use: Authorization: Api-Key sk-..."

    def has_permission(self, request, view):
        # request.auth est l'objet PublicAPIKey si l'auth a réussi
        return (
            request.user is not None
            and request.user.is_authenticated
            and request.auth is not None
        )


class HasSufficientQuota(BasePermission):
    """
    Vérifie que l'utilisateur dispose du quota mensuel nécessaire.
    Doit être utilisé APRÈS IsAPIKeyAuthenticated.

    Usage dans la vue :
        permission_classes = [IsAPIKeyAuthenticated, HasSufficientQuota]

    La vue doit définir `self.get_api_quota_cost()` ou laisser le défaut à 1.
    """
    message = "Monthly quota exceeded."

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            # Les lectures ne consomment pas de quota
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

        # Attache le quota à la requête pour l'incrémenter après succès
        request._quota = quota
        return True