from django.db import models
from django.contrib.auth.models import User
from django.core.validators import URLValidator
from datetime import timedelta
from django.utils import timezone
from django.db import models
import logging
from django.contrib.auth import get_user_model
User = get_user_model()
logger = logging.getLogger(__name__)



class API(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    url = models.URLField(validators=[URLValidator()])
    auth_required = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_apis', null=True, blank=True)
    api_key_encrypted = models.CharField(blank=True, null=True)
    is_blocked = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # 🆕 NEW FIELD: Quota cost per call
    quota_cost = models.PositiveIntegerField(
        default=1,
        help_text="Number of credits consumed per call to this API"
    )

    def can_be_accessed_by(self, user):
        """Only creator or admin can access an API."""
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return self.created_by == user

    def is_public(self):
        return self.visibility == 'public' and not self.is_blocked

    def __str__(self):
        return f"{self.name} (Coût: {self.quota_cost} crédit{'s' if self.quota_cost > 1 else ''})"


# api_management/models.py

class OAuthConfig(models.Model):
    GRANT_TYPE_CHOICES = [
        ('client_credentials', 'Client Credentials'),
        ('authorization_code', 'Authorization Code'),
        ('password', 'Resource Owner Password'),
    ]

    api = models.OneToOneField(
        API, 
        on_delete=models.CASCADE, 
        related_name='oauth_config'
    )
    grant_type = models.CharField(
        max_length=30, 
        choices=GRANT_TYPE_CHOICES, 
        default='client_credentials'
    )
    token_url = models.URLField(
        help_text="URL du serveur OAuth pour obtenir le token"
    )
    client_id = models.CharField(max_length=255)
    client_secret_encrypted = models.CharField(max_length=512)
    scope = models.CharField(
        max_length=512, 
        blank=True, 
        null=True,
        help_text="Scopes séparés par des espaces (ex: read write)"
    )
    # For Authorization Code only
    redirect_uri = models.URLField(blank=True, null=True)
    authorization_url = models.URLField(blank=True, null=True)

    # Token cache
    access_token = models.TextField(blank=True, null=True)
    token_expires_at = models.DateTimeField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)

    def is_token_valid(self):
        if not self.access_token:
            return False
        # token_expires_at NULL = token permanent (ex: GitHub)

        if not self.token_expires_at:
            return True
        try:
            return timezone.now() < self.token_expires_at - timedelta(seconds=60)
        except Exception:
            return False
    def __str__(self):
        return f"OAuth2 [{self.grant_type}] → {self.api.name}"

        
class Endpoint(models.Model):
    api = models.ForeignKey(API, on_delete=models.CASCADE, related_name='endpoints')
    path = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    user_input_required = models.BooleanField(default=False)
    example_request = models.TextField(blank=True, null=True)
    example_response = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.api.name} - {self.path}"





class Parameter(models.Model):
    PARAMETER_TYPE_CHOICES = [
        ('query', 'Query Parameter'),
        ('path', 'Path Parameter'),
        ('body', 'Body Parameter'),
    ]
    DATA_TYPE_CHOICES = [
        ('INTEGER', 'Integer'),
        ('STRING', 'String'),
        ('BOOLEAN', 'Boolean'),
        ('DATE', 'Date'),
        ('JSON', 'json'),
    ]
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE, related_name='parameters')
    name = models.CharField(max_length=100)
    chat_value = models.CharField(max_length=100,default= 'name') # Valeur par défaut pour les interactions de type chat
    param_type = models.CharField(max_length=10, choices=PARAMETER_TYPE_CHOICES)
    data_type = models.CharField(max_length=10, choices=DATA_TYPE_CHOICES, default='STRING')
    required = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    default_value = models.CharField(max_length=255, blank=True, null=True)
    is_in_url = models.BooleanField(default=False)
    is_in_body = models.BooleanField(default=True)
    stored_value = models.CharField(max_length=255, blank=True, null=True)
    editable = models.BooleanField(default=True)  # Nouvelle option
    order = models.PositiveIntegerField(default=0)



    def __str__(self):
        return f"{self.endpoint.api.name} - {self.endpoint.path} ({self.name})"


class Header(models.Model):
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE, related_name='headers')
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.endpoint.api.name} - {self.endpoint.path} ({self.name}: {self.value})"

class Method(models.Model):
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
    ]
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE, related_name='methods')
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    return_code = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.endpoint.api.name} - {self.endpoint.path} [{self.method}]"

class APILog(models.Model):
    session_id = models.CharField(max_length=40, null=True, blank=True)  # Associer la session
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    api = models.ForeignKey(API, on_delete=models.CASCADE)
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE)
    method = models.CharField(max_length=10, choices=Method.METHOD_CHOICES)
    request_data = models.JSONField()
    response_data = models.JSONField()
    status_code = models.IntegerField()
    timestamp = models.DateTimeField(default=timezone.now)
    response_size = models.PositiveIntegerField(default=0) 

    def __str__(self):
        return f"{self.user} - {self.api} ({self.status_code})"

class APIRequestLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    api = models.ForeignKey(API, on_delete=models.CASCADE)
    endpoint = models.ForeignKey(Endpoint, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} a appelé {self.api.name} le {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"




class APICallQuota(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    call_count = models.PositiveIntegerField(default=0)

    month = models.PositiveIntegerField(default=1)
    year = models.PositiveIntegerField(default=timezone.now().year)

    # ✅ IMPORTANT: null=True for unlimited
    monthly_limit = models.PositiveIntegerField(null=True, blank=True, default=100)

    class Meta:
        unique_together = ('user', 'month', 'year')

    def __str__(self):
        limit = "∞" if self.monthly_limit is None else self.monthly_limit
        return f"{self.user.username} - {self.month}/{self.year} ({self.call_count}/{limit})"

    @property
    def is_unlimited(self):
        return self.monthly_limit is None

    @classmethod
    def get_or_create_for_user(cls, user):
        from django.utils import timezone

        today = timezone.now()
        current_month = today.month
        current_year = today.year

        quota, created = cls.objects.get_or_create(
            user=user,
            month=current_month,
            year=current_year,
            defaults={
                "date": today.date(),
                "call_count": 0,
                "monthly_limit": 100,  # fixed limit
            }
        )

        return quota

    # ✅ CHECK QUOTA
    def has_sufficient_quota(self, cost):
        if self.monthly_limit is None:
            return True
        return (self.call_count + cost) <= self.monthly_limit

    # ✅ INCREMENT
    def increment_call_count(self, cost=1):
        self.call_count += cost
        self.save(update_fields=["call_count"])

    @property
    def remaining_calls(self):
        if self.monthly_limit is None:
            return None  # important pour frontend
        return max(0, self.monthly_limit - self.call_count)

    @property
    def usage_percentage(self):
        if self.monthly_limit in (0, None):
            return 0
        return min(100, (self.call_count / self.monthly_limit) * 100)
    
