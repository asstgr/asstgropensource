from django.contrib import admin
from .models import PublicAPIKey
# Register your models here.



@admin.register(PublicAPIKey)
class PublicAPIKeyAdmin(admin.ModelAdmin):
    list_display = ["user", "name", "short_key", "is_active", "created_at", "last_used_at", "expires_at"]
    list_filter = ["is_active"]
    search_fields = ["user__email", "name", "key"]
    readonly_fields = ["key", "created_at", "last_used_at"]
    actions = ["revoke_keys"]

    def short_key(self, obj):
        return f"{obj.key[:12]}..."
    short_key.short_description = "Key"

    @admin.action(description="Revoke selected API keys")
    def revoke_keys(self, request, queryset):
        queryset.update(is_active=False)