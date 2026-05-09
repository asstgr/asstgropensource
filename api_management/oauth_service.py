import requests
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class OAuthService:

    # ─────────────────────────────────────────────
    # FETCH TOKENS
    # ─────────────────────────────────────────────

    @staticmethod
    def fetch_token_client_credentials(oauth_config):
        """Flow Client Credentials : token direct sans user."""
        response = requests.post(
            oauth_config.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": oauth_config.client_id,
                "client_secret": oauth_config.client_secret_encrypted,
                "scope": oauth_config.scope or "",
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def fetch_token_authorization_code(oauth_config, code):
        """Exchange an authorization code for a token."""
        response = requests.post(
            oauth_config.token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": oauth_config.redirect_uri,
                "client_id": oauth_config.client_id,
                "client_secret": oauth_config.client_secret_encrypted,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            timeout=10
        )

        # Log the raw response for debug
        try:
            raw = response.json()
            logger.debug(f"Token response: {raw}")
        except Exception:
            logger.debug(f"Token response (raw): {response.text}")

        response.raise_for_status()
        return response.json()

    @staticmethod
    def refresh_access_token(oauth_config):
        """
        Refreshes the token via refresh_token.
        GitHub and Google compatible.
        """
        if not oauth_config.refresh_token:
            raise ValueError("No refresh token available.")

        response = requests.post(
            oauth_config.token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": oauth_config.refresh_token,
                "client_id": oauth_config.client_id,
                "client_secret": oauth_config.client_secret_encrypted,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        # Google does not always return a new refresh_token
        # → we keep the old one if it’s missing in the answer
        if "refresh_token" not in data and oauth_config.refresh_token:
            data["refresh_token"] = oauth_config.refresh_token

        return data

    # ─────────────────────────────────────────────
    # SAVE TOKEN
    # ─────────────────────────────────────────────

    @classmethod
    def save_token(cls, oauth_config, token_data):
        """
        Save the token to the database.
        - Google: expires_in = 3600 + refresh_token
        - GitHub: pas d'expires_in → token permanently
        """
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError(
                f"No access_token in response. "
                f"Got: {list(token_data.keys())}"
            )

        expires_in = token_data.get("expires_in")
        oauth_config.access_token = access_token

        if expires_in:
            # Token with expiration (Google : 3600s)
            oauth_config.token_expires_at = (
                timezone.now() + timedelta(seconds=int(expires_in))
            )
        else:
            # Permanent token (GitHub) → NULL = valid indefinitely
            oauth_config.token_expires_at = None

        # Refresh token: only overwrites it if it is present
        if token_data.get("refresh_token"):
            oauth_config.refresh_token = token_data["refresh_token"]

        oauth_config.save(update_fields=[
            "access_token", "token_expires_at", "refresh_token"
        ])

        logger.info(
            f"✅ Token saved for '{oauth_config.api.name}' | "
            f"expires_in={expires_in}s | "
            f"has_refresh={bool(oauth_config.refresh_token)}"
        )

    # ─────────────────────────────────────────────
    # GET VALID TOKEN
    # ─────────────────────────────────────────────

    @classmethod
    def get_valid_token(cls, oauth_config):
        """
        Returns a valid token.
        Order: cache → refresh → client_credentials → error
        """
        # Recharge from the DB to avoid the Django cache
        oauth_config.refresh_from_db()

        # 1. No token at all
        if not oauth_config.access_token:
            raise ValueError(
                f"No token found. Please connect via OAuth: "
                f"/api/oauth/authorize/{oauth_config.api.id}/"
            )

        # 2. Token still valid → immediate return
        if oauth_config.is_token_valid():
            logger.debug(f"✅ Token valid for '{oauth_config.api.name}'")
            return oauth_config.access_token

        # 3. Token expired → automatic refresh attempt
        if oauth_config.refresh_token:
            try:
                logger.info(
                    f"♻️ Token expired for '{oauth_config.api.name}', "
                    f"attempting refresh..."
                )
                token_data = cls.refresh_access_token(oauth_config)
                cls.save_token(oauth_config, token_data)
                logger.info(f"✅ Token refreshed for '{oauth_config.api.name}'")
                return oauth_config.access_token
            except Exception as e:
                logger.warning(
                    f"⚠️ Refresh failed for '{oauth_config.api.name}': {e}"
                )

        # 4. Client Credentials → new automated token
        if oauth_config.grant_type == "client_credentials":
            logger.info(
                f"🔑 Fetching new token via client_credentials "
                f"for '{oauth_config.api.name}'"
            )
            token_data = cls.fetch_token_client_credentials(oauth_config)
            cls.save_token(oauth_config, token_data)
            return oauth_config.access_token

        # 5. Authorization Code without a valid refresh → manual reconnection
        raise ValueError(
            f"Token expired and refresh failed. "
            f"Please reconnect via OAuth: "
            f"/api/oauth/authorize/{oauth_config.api.id}/"
        )