"""
Limites fixes pour la création de ressources via l'API publique.
Modifie ces constantes pour ajuster les quotas globaux.
"""

# ── Limites globales ──────────────────────────────────────────
LIMITS = {
    "apis":           100,    # APIs max par utilisateur
    "endpoints":      10,   # Endpoints max par API
    "parameters":     15,   # Paramètres max par endpoint
    "headers":        10,   # Headers max par endpoint
    "api_keys":       5,    # Clés API publiques max par utilisateur
}


# ── Messages d'erreur associés ────────────────────────────────
LIMIT_MESSAGES = {
    "apis":       f"Maximum {LIMITS['apis']} APIs allowed per account.",
    "endpoints":  f"Maximum {LIMITS['endpoints']} endpoints allowed per API.",
    "parameters": f"Maximum {LIMITS['parameters']} parameters allowed per endpoint.",
    "headers":    f"Maximum {LIMITS['headers']} headers allowed per endpoint.",
    "api_keys":   f"Maximum {LIMITS['api_keys']} active API keys allowed.",
}


def check_limit(resource: str, current_count: int) -> tuple[bool, str | None]:
    """
    Vérifie si une limite est atteinte.

    Returns:
        (True, None)          → sous la limite, création autorisée
        (False, error_msg)    → limite atteinte, création refusée
    """
    limit = LIMITS.get(resource)
    if limit is None:
        return True, None

    if current_count >= limit:
        return False, LIMIT_MESSAGES[resource]

    return True, None


def get_limits_summary() -> dict:
    """Retourne un résumé lisible des limites pour l'exposer via l'API."""
    return {
        "max_apis_per_account":        LIMITS["apis"],
        "max_endpoints_per_api":       LIMITS["endpoints"],
        "max_parameters_per_endpoint": LIMITS["parameters"],
        "max_headers_per_endpoint":    LIMITS["headers"],
        "max_api_keys_per_account":    LIMITS["api_keys"],
    }