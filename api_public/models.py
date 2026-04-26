from django.db import models
import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


# Create your models here.


def generate_api_key():
    """Génère une clé API unique au format 'sk-xxxxxxxxxxxxxxxxxxxx'"""
    return f"sk-{uuid.uuid4().hex}{uuid.uuid4().hex[:8]}"


class PublicAPIKey(models.Model):
    """
    Clé API publique pour accéder à la REST API du SaaS.
    Chaque utilisateur peut en avoir plusieurs (ex: dev, prod).
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
        help_text="Nom de la clé (ex: 'Production', 'Dev local')"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Laisser vide pour une clé sans expiration"
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
        """Met à jour last_used_at sans déclencher auto_now sur d'autres champs"""
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at"])

    def revoke(self):
        self.is_active = False
        self.save(update_fields=["is_active"])