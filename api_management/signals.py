import shutil
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.conf import settings
from .models import API
import os

@receiver(post_delete, sender=API)
def delete_api_image_folder(sender, instance, **kwargs):
    # Utiliser created_by_id au lieu de created_by
    created_by_id = getattr(instance, 'created_by_id', None)
    if created_by_id:
        folder = os.path.join(settings.MEDIA_ROOT, f'api_images/user_{created_by_id}/api_{instance.id}')
        if os.path.exists(folder):
            shutil.rmtree(folder)
