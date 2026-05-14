from django.db import models
import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


# Create your models here.


def generate_api_key():
    """Generates a unique API key in the format 'sk-xxxxxxxxxxxxxxxxxxxx'"""
    return f"sk-{uuid.uuid4().hex}{uuid.uuid4().hex[:8]}"


class PublicAPIKey(models.Model):
    """
    Public API key for accessing the SaaS REST API.
    Each user can have multiple keys (e.g., dev, prod).
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="public_api_keys"
    )
    key = models.CharField(
        max_length=80,
        unique=True,
        default=generate_api_key,
        editable=False,
    )
    name = models.CharField(
        max_length=100,
        help_text="Key name (e.g. 'Production', 'Local Dev')"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Leave blank for a key without expiration"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Public API Key"
        verbose_name_plural = "Public API Keys"

    def __str__(self):
        return f"{self.user.email} — {self.name} ({'active' if self.is_active else 'revoked'})"

    @property
    def is_expired(self):
        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return self.is_active and not self.is_expired

    def mark_used(self):
        """Updates last_used_at without triggering auto_now on other fields"""
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at"])

    def revoke(self):
        self.is_active = False
        self.save(update_fields=["is_active"])