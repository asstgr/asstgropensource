from django.urls import path
from . import views

app_name = "api_public"

urlpatterns = [

    # ── Clés API ──────────────────────────────────────────────
    path("keys/",
         views.APIKeyListCreateView.as_view(), name="key-list-create"),
    path("keys/<int:pk>/",
         views.APIKeyRevokeView.as_view(), name="key-revoke"),

    # ── Quota & Limites ───────────────────────────────────────
    path("quota/",
         views.QuotaStatusView.as_view(), name="quota-status"),
    path("limits/",
         views.LimitsView.as_view(), name="limits"),

    # ── APIs ──────────────────────────────────────────────────
    path("apis/",
         views.UserAPIListCreateView.as_view(), name="api-list-create"),
    path("apis/<int:api_id>/",
         views.UserAPIDetailView.as_view(), name="api-detail"),

    # ── Endpoints ─────────────────────────────────────────────
    path("apis/<int:api_id>/endpoints/",
         views.EndpointListCreateView.as_view(), name="endpoint-list-create"),
    path("apis/<int:api_id>/endpoints/<int:endpoint_id>/",
         views.EndpointDetailView.as_view(), name="endpoint-detail"),

    # ── Paramètres ────────────────────────────────────────────
    path("apis/<int:api_id>/endpoints/<int:endpoint_id>/parameters/",
         views.ParameterListCreateView.as_view(), name="parameter-list-create"),
    path("apis/<int:api_id>/endpoints/<int:endpoint_id>/parameters/<int:param_id>/",
         views.ParameterDetailView.as_view(), name="parameter-detail"),

    # ── Headers ───────────────────────────────────────────────
    path("apis/<int:api_id>/endpoints/<int:endpoint_id>/headers/",
         views.HeaderListCreateView.as_view(), name="header-list-create"),
    path("apis/<int:api_id>/endpoints/<int:endpoint_id>/headers/<int:header_id>/",
         views.HeaderDetailView.as_view(), name="header-detail"),

    # ── Méthodes ──────────────────────────────────────────────
    path("apis/<int:api_id>/endpoints/<int:endpoint_id>/methods/",
         views.MethodListCreateView.as_view(), name="method-list-create"),
    path("apis/<int:api_id>/endpoints/<int:endpoint_id>/methods/<int:method_id>/",
         views.MethodDetailView.as_view(), name="method-detail"),

    # ── Exécution ─────────────────────────────────────────────
    path("apis/<int:api_id>/endpoints/<int:endpoint_id>/execute/",
         views.ExecuteEndpointView.as_view(), name="endpoint-execute"),

     # OAuth
    path('apis/<int:api_id>/oauth/',        views.OAuthConfigView.as_view(),      name='oauth-config'),
    path('apis/<int:api_id>/oauth/token/',  views.OAuthTokenStatusView.as_view(), name='oauth-token-status'),
]