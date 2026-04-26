from django.apps import AppConfig
from django.conf import settings
from django.utils.module_loading import import_string


class ApiManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api_management'

    def ready(self):
        import api_management.signals
