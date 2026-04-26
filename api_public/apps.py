from django.apps import AppConfig


class ApiPublicConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api_public'
    verbose_name = "Public REST API"
