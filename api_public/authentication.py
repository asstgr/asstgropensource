from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import PublicAPIKey


class APIKeyAuthentication(BaseAuthentication):
    """
    Authentification via header :
        Authorization: Api-Key sk-xxxxxxxxxxxxxxxxxxxx
    ou via query param (fallback) :
        ?api_key=sk-xxxxxxxxxxxxxxxxxxxx
    """

    keyword = "Api-Key"

    def authenticate(self, request):
        # 1. Cherche dans le header Authorization
        auth_header = request.headers.get("Authorization", "")
        api_key_value = None

        if auth_header.startswith(f"{self.keyword} "):
            api_key_value = auth_header[len(self.keyword) + 1:].strip()

        # 2. Fallback : query param ?api_key=...
        if not api_key_value:
            api_key_value = request.query_params.get("api_key", "").strip()

        if not api_key_value:
            return None  # Pas d'auth → laisse passer aux autres backends

        # 3. Récupère la clé en base
        try:
            api_key_obj = PublicAPIKey.objects.select_related("user").get(key=api_key_value)
        except PublicAPIKey.DoesNotExist:
            raise AuthenticationFailed("Invalid API key.")

        # 4. Vérifie validité
        if not api_key_obj.is_valid:
            if api_key_obj.is_expired:
                raise AuthenticationFailed("API key expired.")
            raise AuthenticationFailed("API key revoked.")

        # 5. Marque la date d'utilisation (async-safe via update_fields)
        api_key_obj.mark_used()

        # Retourne (user, api_key_obj) — api_key_obj accessible via request.auth
        return (api_key_obj.user, api_key_obj)

    def authenticate_header(self, request):
        return f'{self.keyword} realm="api"'