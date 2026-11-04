from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible
import os


@deconstructible
class PrivateStorage(FileSystemStorage):
    @property
    def location(self):
        return os.path.abspath(settings.PRIVATE_MEDIA_ROOT)

    @property
    def base_location(self):
        return settings.PRIVATE_MEDIA_ROOT

    def url(self, name):
        raise ValueError('Private documents have no public URL. Use an authenticated download.')


private_storage = PrivateStorage()
