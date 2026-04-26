from rest_framework import serializers
from api_management.models import API, Endpoint, Parameter, Header, Method, OAuthConfig
from .models import PublicAPIKey


# ──────────────────────────────────────────────
# API Key
# ──────────────────────────────────────────────


class PublicAPIKeySerializer(serializers.ModelSerializer):
    key = serializers.CharField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = PublicAPIKey
        fields = [
            "id", "name", "key",
            "is_active", "is_expired", "is_valid",
            "created_at", "last_used_at", "expires_at",
        ]
        read_only_fields = ["id", "key", "created_at", "last_used_at"]


# ──────────────────────────────────────────────
# Parameter
# ──────────────────────────────────────────────

class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = [
            "id", "name", "param_type", "data_type",
            "required", "description", "default_value",
            "is_in_url", "is_in_body", "editable", "order",
            "stored_value", "chat_value",
        ]


class ParameterCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = [
            "name", "param_type", "data_type",
            "required", "description", "default_value",
            "is_in_url", "is_in_body", "editable", "order",
            "stored_value", "chat_value",
        ]

    def validate_param_type(self, value):
        allowed = [c[0] for c in Parameter.PARAMETER_TYPE_CHOICES]
        if value not in allowed:
            raise serializers.ValidationError(f"param_type must be one of: {allowed}")
        return value

    def validate_data_type(self, value):
        allowed = [c[0] for c in Parameter.DATA_TYPE_CHOICES]
        if value not in allowed:
            raise serializers.ValidationError(f"data_type must be one of: {allowed}")
        return value


# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────

class HeaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Header
        fields = ["id", "name", "value"]


class HeaderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Header
        fields = ["name", "value"]

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Header name cannot be empty.")
        return value.strip()


# ──────────────────────────────────────────────
# Method
# ──────────────────────────────────────────────

class MethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Method
        fields = ["id", "method", "return_code"]


class MethodCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Method
        fields = ["method", "return_code"]

    def validate_method(self, value):
        allowed = [c[0] for c in Method.METHOD_CHOICES]
        if value not in allowed:
            raise serializers.ValidationError(f"method must be one of: {allowed}")
        return value


# ──────────────────────────────────────────────
# Endpoint
# ──────────────────────────────────────────────

class EndpointSerializer(serializers.ModelSerializer):
    parameters = ParameterSerializer(many=True, read_only=True)
    headers = HeaderSerializer(many=True, read_only=True)
    methods = MethodSerializer(many=True, read_only=True)

    class Meta:
        model = Endpoint
        fields = [
            "id", "path", "description",
            "user_input_required",
            "example_request", "example_response",
            "parameters", "headers", "methods",
        ]


class EndpointListSerializer(serializers.ModelSerializer):
    method_list = serializers.SerializerMethodField()
    parameter_count = serializers.SerializerMethodField()
    header_count = serializers.SerializerMethodField()

    class Meta:
        model = Endpoint
        fields = [
            "id", "path", "description",
            "user_input_required",
            "method_list", "parameter_count", "header_count",
        ]

    def get_method_list(self, obj):
        return list(obj.methods.values_list("method", flat=True))

    def get_parameter_count(self, obj):
        return obj.parameters.count()

    def get_header_count(self, obj):
        return obj.headers.count()


class EndpointCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Endpoint
        fields = [
            "path", "description",
            "user_input_required",
            "example_request", "example_response",
        ]

    def validate_path(self, value):
        if not value.startswith("/"):
            value = "/" + value
        return value


# ──────────────────────────────────────────────
# API
# ──────────────────────────────────────────────

class APIListSerializer(serializers.ModelSerializer):
    endpoint_count = serializers.SerializerMethodField()

    class Meta:
        model = API
        fields = [
            "id", "name", "description", "url",
            "visibility", "is_active", "quota_cost",
            "endpoint_count",
        ]

    def get_endpoint_count(self, obj):
        return obj.endpoints.count()


class APIDetailSerializer(serializers.ModelSerializer):
    endpoints = EndpointListSerializer(many=True, read_only=True)

    class Meta:
        model = API
        fields = [
            "id", "name", "description", "url",
            "auth_required", "visibility", "is_active",
            "quota_cost", "endpoints",
        ]


class APICreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = API
        fields = [
            "name", "description", "url",
            "auth_required", "visibility",
            "is_active", "quota_cost",
        ]

    def validate_url(self, value):
        if not value.startswith(("http://", "https://")):
            raise serializers.ValidationError("URL must start with http:// or https://")
        return value.rstrip("/")

    def validate_quota_cost(self, value):
        if value < 1:
            raise serializers.ValidationError("quota_cost must be at least 1.")
        if value > 100:
            raise serializers.ValidationError("quota_cost cannot exceed 100.")
        return value


# ──────────────────────────────────────────────
# Execute
# ──────────────────────────────────────────────

class ExecuteRequestSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=["GET", "POST", "PUT", "DELETE"])
    params = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        required=False,
        default=dict,
    )
    display_format = serializers.ChoiceField(
        choices=["json", "compact", "standard", "verbose"],
        default="json",
    )



# ──────────────────────────────────────────────
# 0AUTH 2.0
# ──────────────────────────────────────────────


class OAuthConfigSerializer(serializers.ModelSerializer):
    is_token_valid = serializers.BooleanField(read_only=True)
    token_expires_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = OAuthConfig
        fields = [
            'id', 'grant_type', 'token_url', 'client_id',
            'client_secret_encrypted', 'scope',
            'redirect_uri', 'authorization_url',
            'is_token_valid', 'token_expires_at',
        ]
        extra_kwargs = {
            'client_secret_encrypted': {'write_only': True},
            'token_expires_at': {'read_only': True},
        }

    def validate(self, data):
        grant_type = data.get('grant_type')
        if grant_type == 'authorization_code':
            if not data.get('redirect_uri'):
                raise serializers.ValidationError(
                    {'redirect_uri': 'Required for authorization_code flow.'}
                )
            if not data.get('authorization_url'):
                raise serializers.ValidationError(
                    {'authorization_url': 'Required for authorization_code flow.'}
                )
        return data


class APIDetailSerializer(serializers.ModelSerializer):
    endpoints = EndpointListSerializer(many=True, read_only=True)
    oauth_config = OAuthConfigSerializer(read_only=True)  # ← ajoute ça

    class Meta:
        model = API
        fields = [
            'id', 'name', 'description', 'url',
            'auth_required', 'visibility', 'is_active',
            'quota_cost', 'endpoints',
            'oauth_config',  # ← ajoute ça
        ]