# api/throttling.py

from rest_framework.throttling import SimpleRateThrottle


class APIKeyBurstThrottle(SimpleRateThrottle):
    scope = "api_burst"

    def get_cache_key(self, request, view):
        if not request.auth:
            return None
        return f"throttle_{request.auth.key}"


class APIKeySustainedThrottle(SimpleRateThrottle):
    scope = "api_sustained"

    def get_cache_key(self, request, view):
        if not request.auth:
            return None
        return f"throttle_{request.auth.key}"