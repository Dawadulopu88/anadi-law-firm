"""Explicit HTTPS deployment settings; local demonstrations keep config.settings."""
from urllib.parse import urlsplit
from django.core.exceptions import ImproperlyConfigured
from .settings import *  # noqa: F403

DEBUG = False
SECRET_KEY = config('PRODUCTION_SECRET_KEY', default='')
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith('django-insecure-'):
    raise ImproperlyConfigured('Set a strong, independently generated PRODUCTION_SECRET_KEY (50+ characters).')

ALLOWED_HOSTS = config('PRODUCTION_ALLOWED_HOSTS', default='', cast=Csv())
if not ALLOWED_HOSTS or any(not h or '*' in h or '://' in h or '/' in h for h in ALLOWED_HOSTS):
    raise ImproperlyConfigured('Set explicit PRODUCTION_ALLOWED_HOSTS without wildcards or URL schemes.')


def https_origins(name):
    origins = config(name, default='', cast=Csv())
    for origin in origins:
        parsed = urlsplit(origin)
        if parsed.scheme != 'https' or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username or '*' in origin:
            raise ImproperlyConfigured(f'{name} must contain exact HTTPS origins without paths.')
    return origins


CORS_ALLOWED_ORIGINS = https_origins('PRODUCTION_CORS_ALLOWED_ORIGINS')
CSRF_TRUSTED_ORIGINS = https_origins('PRODUCTION_CSRF_TRUSTED_ORIGINS')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = config('PRODUCTION_HSTS_SECONDS', default=3600, cast=int)
if SECURE_HSTS_SECONDS < 1:
    raise ImproperlyConfigured('PRODUCTION_HSTS_SECONDS must be positive.')
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('PRODUCTION_HSTS_INCLUDE_SUBDOMAINS', default=False, cast=bool)
SECURE_HSTS_PRELOAD = config('PRODUCTION_HSTS_PRELOAD', default=False, cast=bool)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# Waitress normalizes the client IP and scheme only for its configured trusted
# proxy. Django itself does not trust arbitrary forwarded headers.
REST_FRAMEWORK = {**REST_FRAMEWORK, 'NUM_PROXIES': 0}
SECURE_PROXY_SSL_HEADER = None
USE_X_FORWARDED_HOST = False
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
                      'LOCATION': 'lawfirm_cache', 'TIMEOUT': 300}}

data_dir = config('PRODUCTION_DATA_ROOT', default='')
if not data_dir or not Path(data_dir).is_absolute():
    raise ImproperlyConfigured('PRODUCTION_DATA_ROOT must be an absolute persistent directory.')
DATA_ROOT = Path(data_dir).resolve()
MEDIA_ROOT = DATA_ROOT / 'public_media'
PRIVATE_MEDIA_ROOT = DATA_ROOT / 'private_media'
STATIC_ROOT = DATA_ROOT / 'staticfiles'
# Avoid traceback emails/console email containing business information.
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
