from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from api_management.models import API, Endpoint, Parameter, Header, Method
from api_management.models import APICallQuota, APILog, APIRequestLog, OAuthConfig
from api_management.utils import (
    get_endpoint_details, validate_and_process_parameters,
    prepare_headers, fill_url_path, send_api_request2,
    process_api_response, log_api_call2,
)
from .authentication import APIKeyAuthentication
from .permissions import IsAPIKeyAuthenticated, HasSufficientQuota
from .serializers import (
    PublicAPIKeySerializer,
    APIListSerializer, APIDetailSerializer, APICreateSerializer,
    EndpointSerializer, EndpointListSerializer, EndpointCreateSerializer,
    ParameterSerializer, ParameterCreateSerializer,
    HeaderSerializer, HeaderCreateSerializer,
    MethodSerializer, MethodCreateSerializer,
    ExecuteRequestSerializer, OAuthConfigSerializer,
)
from .models import PublicAPIKey
from .limits import check_limit, get_limits_summary, LIMITS


# ──────────────────────────────────────────────────────────────
# 🔑 API Keys
# ──────────────────────────────────────────────────────────────

class APIKeyListCreateView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def get(self, request):
        keys = PublicAPIKey.objects.filter(user=request.user)
        return Response(PublicAPIKeySerializer(keys, many=True).data)

    def post(self, request):
        count = PublicAPIKey.objects.filter(user=request.user, is_active=True).count()
        allowed, msg = check_limit("api_keys", count)
        if not allowed:
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        serializer = PublicAPIKeySerializer(data=request.data)
        if serializer.is_valid():
            key_obj = serializer.save(user=request.user)
            data = PublicAPIKeySerializer(key_obj).data
            data["key"] = key_obj.key
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class APIKeyRevokeView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def delete(self, request, pk):
        key_obj = get_object_or_404(PublicAPIKey, pk=pk, user=request.user)
        key_obj.revoke()
        return Response({"detail": "API key revoked."})


# ──────────────────────────────────────────────────────────────
# 📋 Limits
# ──────────────────────────────────────────────────────────────

class LimitsView(APIView):
    """GET /api/v1/limits/ — active limits + current usage."""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def get(self, request):
        api_count = API.objects.filter(created_by=request.user).count()
        key_count = PublicAPIKey.objects.filter(user=request.user, is_active=True).count()
        return Response({
            "limits": get_limits_summary(),
            "current_usage": {
                "apis":     {"used": api_count, "max": LIMITS["apis"]},
                "api_keys": {"used": key_count, "max": LIMITS["api_keys"]},
            },
        })


# ──────────────────────────────────────────────────────────────
# 📚 APIs — CRUD
# ──────────────────────────────────────────────────────────────

class UserAPIListCreateView(APIView):
    """
    GET  /api/v1/apis/  → list the user's APIs
    POST /api/v1/apis/  → create a new API (limited to LIMITS["apis"])
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def get(self, request):
        if request.user.is_superuser:
            apis = API.objects.filter(is_active=True, is_blocked=False)
        else:
            apis = API.objects.filter(
                created_by=request.user, is_active=True, is_blocked=False,
            )
        return Response({"count": apis.count(), "results": APIListSerializer(apis, many=True).data})

    def post(self, request):
        count = API.objects.filter(created_by=request.user).count()
        allowed, msg = check_limit("apis", count)
        if not allowed:
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        serializer = APICreateSerializer(data=request.data)
        if serializer.is_valid():
            api = serializer.save(created_by=request.user)
            return Response(APIDetailSerializer(api).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserAPIDetailView(APIView):
    """GET / PATCH / DELETE /api/v1/apis/<api_id>/"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def _get_api(self, request, api_id, owned=False):
        if owned:
            return get_object_or_404(API, pk=api_id, created_by=request.user)
        api = get_object_or_404(API, pk=api_id, is_blocked=False)
        if not api.can_be_accessed_by(request.user):
            return None
        return api

    def get(self, request, api_id):
        api = self._get_api(request, api_id)
        if not api:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(APIDetailSerializer(api).data)

    def patch(self, request, api_id):
        api = self._get_api(request, api_id, owned=True)
        serializer = APICreateSerializer(api, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(APIDetailSerializer(api).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, api_id):
        api = self._get_api(request, api_id, owned=True)
        api.delete()
        return Response({"detail": "API deleted."}, status=status.HTTP_204_NO_CONTENT)


# ──────────────────────────────────────────────────────────────
# 🔗 Endpoints — CRUD
# ──────────────────────────────────────────────────────────────

class EndpointListCreateView(APIView):
    """
    GET  /api/v1/apis/<id>/endpoints/
    POST /api/v1/apis/<id>/endpoints/  (limited to LIMITS["endpoints"])
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def _get_api(self, request, api_id):
        return get_object_or_404(API, pk=api_id, created_by=request.user, is_blocked=False)

    def get(self, request, api_id):
        api = self._get_api(request, api_id)
        endpoints = api.endpoints.all()
        return Response({
            "count": endpoints.count(),
            "max": LIMITS["endpoints"],
            "results": EndpointListSerializer(endpoints, many=True).data,
        })

    def post(self, request, api_id):
        api = self._get_api(request, api_id)
        allowed, msg = check_limit("endpoints", api.endpoints.count())
        if not allowed:
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        serializer = EndpointCreateSerializer(data=request.data)
        if serializer.is_valid():
            endpoint = serializer.save(api=api)
            return Response(EndpointSerializer(endpoint).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EndpointDetailView(APIView):
    """GET / PATCH / DELETE /api/v1/apis/<id>/endpoints/<ep_id>/"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def _get(self, request, api_id, endpoint_id):
        api = get_object_or_404(API, pk=api_id, created_by=request.user)
        return get_object_or_404(Endpoint, pk=endpoint_id, api=api)

    def get(self, request, api_id, endpoint_id):
        return Response(EndpointSerializer(self._get(request, api_id, endpoint_id)).data)

    def patch(self, request, api_id, endpoint_id):
        ep = self._get(request, api_id, endpoint_id)
        s = EndpointCreateSerializer(ep, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return Response(EndpointSerializer(ep).data)
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, api_id, endpoint_id):
        self._get(request, api_id, endpoint_id).delete()
        return Response({"detail": "Endpoint deleted."}, status=status.HTTP_204_NO_CONTENT)


# ──────────────────────────────────────────────────────────────
# ⚙️ Parameters — CRUD
# ──────────────────────────────────────────────────────────────

class ParameterListCreateView(APIView):
    """
    GET  /api/v1/apis/<id>/endpoints/<ep_id>/parameters/
    POST /api/v1/apis/<id>/endpoints/<ep_id>/parameters/  (limited to LIMITS["parameters"])
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def _get_endpoint(self, request, api_id, endpoint_id):
        api = get_object_or_404(API, pk=api_id, created_by=request.user)
        return get_object_or_404(Endpoint, pk=endpoint_id, api=api)

    def get(self, request, api_id, endpoint_id):
        ep = self._get_endpoint(request, api_id, endpoint_id)
        params = ep.parameters.order_by("order")
        return Response({
            "count": params.count(),
            "max": LIMITS["parameters"],
            "results": ParameterSerializer(params, many=True).data,
        })

    def post(self, request, api_id, endpoint_id):
        ep = self._get_endpoint(request, api_id, endpoint_id)
        allowed, msg = check_limit("parameters", ep.parameters.count())
        if not allowed:
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        name = request.data.get("name", "")
        if ep.parameters.filter(name=name).exists():
            return Response(
                {"detail": f"Parameter '{name}' already exists on this endpoint."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        s = ParameterCreateSerializer(data=request.data)
        if s.is_valid():
            param = s.save(endpoint=ep)
            return Response(ParameterSerializer(param).data, status=status.HTTP_201_CREATED)
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)


class ParameterDetailView(APIView):
    """GET / PATCH / DELETE /api/v1/apis/<id>/endpoints/<ep_id>/parameters/<param_id>/"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def _get(self, request, api_id, endpoint_id, param_id):
        api = get_object_or_404(API, pk=api_id, created_by=request.user)
        ep = get_object_or_404(Endpoint, pk=endpoint_id, api=api)
        return get_object_or_404(Parameter, pk=param_id, endpoint=ep)

    def get(self, request, api_id, endpoint_id, param_id):
        return Response(ParameterSerializer(self._get(request, api_id, endpoint_id, param_id)).data)

    def patch(self, request, api_id, endpoint_id, param_id):
        param = self._get(request, api_id, endpoint_id, param_id)
        s = ParameterCreateSerializer(param, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return Response(ParameterSerializer(param).data)
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, api_id, endpoint_id, param_id):
        self._get(request, api_id, endpoint_id, param_id).delete()
        return Response({"detail": "Parameter deleted."}, status=status.HTTP_204_NO_CONTENT)


# ──────────────────────────────────────────────────────────────
# 📨 Headers — CRUD
# ──────────────────────────────────────────────────────────────

class HeaderListCreateView(APIView):
    """
    GET  /api/v1/apis/<id>/endpoints/<ep_id>/headers/
    POST /api/v1/apis/<id>/endpoints/<ep_id>/headers/  (limited to LIMITS["headers"])
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def _get_endpoint(self, request, api_id, endpoint_id):
        api = get_object_or_404(API, pk=api_id, created_by=request.user)
        return get_object_or_404(Endpoint, pk=endpoint_id, api=api)

    def get(self, request, api_id, endpoint_id):
        ep = self._get_endpoint(request, api_id, endpoint_id)
        headers = ep.headers.all()
        return Response({
            "count": headers.count(),
            "max": LIMITS["headers"],
            "results": HeaderSerializer(headers, many=True).data,
        })

    def post(self, request, api_id, endpoint_id):
        ep = self._get_endpoint(request, api_id, endpoint_id)
        allowed, msg = check_limit("headers", ep.headers.count())
        if not allowed:
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        s = HeaderCreateSerializer(data=request.data)
        if s.is_valid():
            header = s.save(endpoint=ep)
            return Response(HeaderSerializer(header).data, status=status.HTTP_201_CREATED)
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)


class HeaderDetailView(APIView):
    """GET / PATCH / DELETE /api/v1/apis/<id>/endpoints/<ep_id>/headers/<h_id>/"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def _get(self, request, api_id, endpoint_id, header_id):
        api = get_object_or_404(API, pk=api_id, created_by=request.user)
        ep = get_object_or_404(Endpoint, pk=endpoint_id, api=api)
        return get_object_or_404(Header, pk=header_id, endpoint=ep)

    def get(self, request, api_id, endpoint_id, header_id):
        return Response(HeaderSerializer(self._get(request, api_id, endpoint_id, header_id)).data)

    def patch(self, request, api_id, endpoint_id, header_id):
        h = self._get(request, api_id, endpoint_id, header_id)
        s = HeaderCreateSerializer(h, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return Response(HeaderSerializer(h).data)
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, api_id, endpoint_id, header_id):
        self._get(request, api_id, endpoint_id, header_id).delete()
        return Response({"detail": "Header deleted."}, status=status.HTTP_204_NO_CONTENT)


# ──────────────────────────────────────────────────────────────
# ⚡ Methods — CRUD
# ──────────────────────────────────────────────────────────────

class MethodListCreateView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def _get_endpoint(self, request, api_id, endpoint_id):
        api = get_object_or_404(API, pk=api_id, created_by=request.user)
        return get_object_or_404(Endpoint, pk=endpoint_id, api=api)

    def get(self, request, api_id, endpoint_id):
        ep = self._get_endpoint(request, api_id, endpoint_id)
        return Response(MethodSerializer(ep.methods.all(), many=True).data)

    def post(self, request, api_id, endpoint_id):
        ep = self._get_endpoint(request, api_id, endpoint_id)
        if ep.methods.count() >= 4:
            return Response(
                {"detail": "Maximum 4 methods per endpoint."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        method_value = request.data.get("method")
        if ep.methods.filter(method=method_value).exists():
            return Response(
                {"detail": f"Method {method_value} already exists on this endpoint."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        s = MethodCreateSerializer(data=request.data)
        if s.is_valid():
            method = s.save(endpoint=ep)
            return Response(MethodSerializer(method).data, status=status.HTTP_201_CREATED)
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)


class MethodDetailView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def delete(self, request, api_id, endpoint_id, method_id):
        api = get_object_or_404(API, pk=api_id, created_by=request.user)
        ep = get_object_or_404(Endpoint, pk=endpoint_id, api=api)
        method = get_object_or_404(Method, pk=method_id, endpoint=ep)
        method.delete()
        return Response({"detail": "Method deleted."}, status=status.HTTP_204_NO_CONTENT)


# ──────────────────────────────────────────────────────────────
# 🚀 Endpoint execution
# ──────────────────────────────────────────────────────────────

class ExecuteEndpointView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated, HasSufficientQuota]

    def post(self, request, api_id, endpoint_id):
        api = get_object_or_404(API, pk=api_id, is_active=True, is_blocked=False)
        if not api.can_be_accessed_by(request.user):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        endpoint = get_object_or_404(Endpoint, pk=endpoint_id, api=api)
        s = ExecuteRequestSerializer(data=request.data)
        if not s.is_valid():
            return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)

        validated = s.validated_data
        selected_method = validated["method"]
        display_format = validated.get("display_format", "json")

        methods, parameters, headers = get_endpoint_details(endpoint)
        method_names = [m.method for m in methods]
        if selected_method not in method_names:
            return Response(
                {"detail": f"Method {selected_method} not supported. Available: {method_names}"},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )

        class FakeRequest:
            POST = validated.get("params", {})
            session = request.session

        user_params, request_data_clean, header_params, body_params, query_params, err = \
            validate_and_process_parameters(FakeRequest(), parameters)

        if err:
            return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)

        request_headers = prepare_headers(headers, api, header_params)
        full_url = api.url.rstrip("/") + "/" + fill_url_path(endpoint.path, user_params).lstrip("/")

        response, error = send_api_request2(
            url=full_url, method=selected_method,
            headers=request_headers, body_params=body_params, query_params=query_params,
        )
        if error:
            return Response({"detail": f"API call failed: {error}"}, status=status.HTTP_502_BAD_GATEWAY)

        try:
            response.raise_for_status()
        except Exception as e:
            return Response({"detail": str(e), "status_code": response.status_code}, status=status.HTTP_502_BAD_GATEWAY)

        formatted = process_api_response(response, display_format, "en")

        quota = getattr(request, "_quota", None)
        if quota:
            quota.increment_call_count(api.quota_cost)

        log_api_call2(
            session_id=None, user_id=request.user.id, api=api, endpoint=endpoint,
            selected_method=selected_method, request_data_clean=request_data_clean,
            response_data=formatted if isinstance(formatted, str) else str(formatted),
            status_code=response.status_code,
        )
        APIRequestLog.objects.create(user=request.user, api=api, endpoint=endpoint)

        quota_obj = quota or APICallQuota.get_or_create_for_user(request.user)
        return Response({
            "status_code": response.status_code,
            "result": formatted,
            "quota": {
                "used": quota_obj.call_count,
                "remaining": quota_obj.remaining_calls,
                "limit": quota_obj.monthly_limit,
                "usage_pct": round(quota_obj.usage_percentage, 1),
            },
        })


# ──────────────────────────────────────────────────────────────
# 📊 Quota
# ──────────────────────────────────────────────────────────────

class QuotaStatusView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def get(self, request):
        quota = APICallQuota.get_or_create_for_user(request.user)
        return Response({
            "month": quota.month, "year": quota.year,
            "used": quota.call_count, "remaining": quota.remaining_calls,
            "limit": quota.monthly_limit, "usage_pct": round(quota.usage_percentage, 1),
        })


# ──────────────────────────────────────────────────────────────
# OAuth 2.0
# ──────────────────────────────────────────────────────────────

class OAuthConfigView(APIView):
    """
    GET    /api/v1/apis/<api_id>/oauth/   → retrieve the OAuth config
    POST   /api/v1/apis/<api_id>/oauth/   → create the OAuth config
    PATCH  /api/v1/apis/<api_id>/oauth/   → update the OAuth config
    DELETE /api/v1/apis/<api_id>/oauth/   → delete the OAuth config
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def _get_api(self, request, api_id):
        return get_object_or_404(API, pk=api_id, created_by=request.user)

    def get(self, request, api_id):
        api = self._get_api(request, api_id)
        if not hasattr(api, 'oauth_config'):
            return Response(
                {'detail': 'No OAuth config for this API.'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(OAuthConfigSerializer(api.oauth_config).data)

    def post(self, request, api_id):
        api = self._get_api(request, api_id)
        if hasattr(api, 'oauth_config'):
            return Response(
                {'detail': 'OAuth config already exists. Use PATCH to update.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        s = OAuthConfigSerializer(data=request.data)
        if s.is_valid():
            s.save(api=api)
            return Response(s.data, status=status.HTTP_201_CREATED)
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, api_id):
        api = self._get_api(request, api_id)
        oauth = get_object_or_404(OAuthConfig, api=api)
        s = OAuthConfigSerializer(oauth, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return Response(s.data)
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, api_id):
        api = self._get_api(request, api_id)
        oauth = get_object_or_404(OAuthConfig, api=api)
        oauth.delete()
        return Response(
            {'detail': 'OAuth config deleted.'},
            status=status.HTTP_204_NO_CONTENT
        )


class OAuthTokenStatusView(APIView):
    """
    GET  /api/v1/apis/<api_id>/oauth/token/  → token status
    POST /api/v1/apis/<api_id>/oauth/token/  → force refresh (client_credentials only)
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyAuthenticated]

    def _get_oauth(self, request, api_id):
        api = get_object_or_404(API, pk=api_id, created_by=request.user)
        return get_object_or_404(OAuthConfig, api=api)

    def get(self, request, api_id):
        oauth = self._get_oauth(request, api_id)
        return Response({
            'grant_type': oauth.grant_type,
            'has_token': bool(oauth.access_token),
            'is_token_valid': oauth.is_token_valid(),
            'token_expires_at': oauth.token_expires_at,
            'has_refresh_token': bool(oauth.refresh_token),
            # Authorization Code: provide the login link
            'authorize_url': (
                f'/api/oauth/authorize/{api_id}/'
                if oauth.grant_type == 'authorization_code'
                else None
            ),
        })

    def post(self, request, api_id):
        """Force refresh — only available for client_credentials."""
        oauth = self._get_oauth(request, api_id)

        if oauth.grant_type != 'client_credentials':
            return Response(
                {'detail': 'Manual token refresh only available for client_credentials flow.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from api_management.oauth_service import OAuthService
            token_data = OAuthService.fetch_token_client_credentials(oauth)
            OAuthService.save_token(oauth, token_data)
            return Response({
                'detail': 'Token refreshed successfully.',
                'is_token_valid': oauth.is_token_valid(),
                'token_expires_at': oauth.token_expires_at,
            })
        except Exception as e:
            return Response(
                {'detail': f'Token refresh failed: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY
            )