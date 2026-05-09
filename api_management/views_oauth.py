# api_management/views_oauth.py

from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.urls import reverse
from api_management.models import API
from api_management.oauth_service import OAuthService
import urllib.parse

@login_required
def oauth_authorize(request, api_id):
    api = get_object_or_404(API, pk=api_id, created_by=request.user)

    if not hasattr(api, 'oauth_config'):
        return HttpResponseBadRequest("Cette API n'a pas de config OAuth2.")

    oauth = api.oauth_config

    if oauth.grant_type != 'authorization_code':
        return HttpResponseBadRequest("Ce flow OAuth ne nécessite pas d'autorisation manuelle.")

    params = {
        "response_type": "code",
        "client_id": oauth.client_id,
        "redirect_uri": oauth.redirect_uri,
        "scope": oauth.scope or "",
        "state": str(api_id),
        "access_type": "offline",   # ← CRUCIAL pour Google : obtenir un refresh_token
        "prompt": "consent",        # ← CRUCIAL : force l'affichage du consentement
    }

    auth_url = oauth.authorization_url + "?" + urllib.parse.urlencode(params)
    return redirect(auth_url)

@login_required
def oauth_callback(request):
    """
    Étape 2 : reçoit le code d'autorisation et l'échange contre un token.
    """
    code = request.GET.get("code")
    state = request.GET.get("state")  # = api_id
    error = request.GET.get("error")

    if error:
        return HttpResponseBadRequest(f"OAuth error: {error}")

    if not code or not state:
        return HttpResponseBadRequest("Paramètres manquants.")

    api = get_object_or_404(API, pk=state, created_by=request.user)
    oauth = api.oauth_config

    try:
        token_data = OAuthService.fetch_token_authorization_code(oauth, code)
        OAuthService.save_token(oauth, token_data)
    except Exception as e:
        return HttpResponseBadRequest(f"Erreur lors de l'échange du token : {e}")

    return redirect(reverse('dash:dashboard'))