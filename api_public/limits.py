"""
Fixed limits for creating assets via the public API.
Modifies these constants to adjust global quotas.
"""

# ── Global limits ──────────────────────────────────────────────
LIMITS = {
    "apis":           100,    # APIs max per user
    "endpoints": 10, #max endpoints per API
    "parameters":  15,  # Max parameters per endpoint
    "headers":  10,  # Headers max per endpoint
    "api_keys":  5, #max public API keys per user
}


# ── error messages associated ────────────────────────────────
LIMIT_MESSAGES = {
    "apis":       f"Maximum {LIMITS['apis']} APIs allowed per account.",
    "endpoints":  f"Maximum {LIMITS['endpoints']} endpoints allowed per API.",
    "parameters": f"Maximum {LIMITS['parameters']} parameters allowed per endpoint.",
    "headers":    f"Maximum {LIMITS['headers']} headers allowed per endpoint.",
    "api_keys":   f"Maximum {LIMITS['api_keys']} active API keys allowed.",
}


def check_limit(resource: str, current_count: int) -> tuple[bool, str | None]:
    """
    Checks if a limit has been reached.

    Returns:
        (True, None)          → under the limit, creation allowed
        (False, error_msg)    → limit reached, creation denied
    """
    limit = LIMITS.get(resource)
    if limit is None:
        return True, None

    if current_count >= limit:
        return False, LIMIT_MESSAGES[resource]

    return True, None


def get_limits_summary() -> dict:
    """Returns a readable summary of the limits for exposure via the API."""
    return {
        "max_apis_per_account":        LIMITS["apis"],
        "max_endpoints_per_api":       LIMITS["endpoints"],
        "max_parameters_per_endpoint": LIMITS["parameters"],
        "max_headers_per_endpoint":    LIMITS["headers"],
        "max_api_keys_per_account":    LIMITS["api_keys"],
    }