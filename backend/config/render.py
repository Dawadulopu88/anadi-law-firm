"""Render's free, temporary demonstration profile (no real client data)."""
import os
import hashlib
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
if not hostname or not hostname.endswith('.onrender.com'):
    raise ImproperlyConfigured('Render demo requires RENDER_EXTERNAL_HOSTNAME ending in .onrender.com.')
os.environ.setdefault('PRODUCTION_ALLOWED_HOSTS', hostname)
render_secret = os.environ.get('SECRET_KEY', '')
if len(render_secret) < 32 or len(set(render_secret)) < 5:
    raise ImproperlyConfigured('Render SECRET_KEY must be an independently generated random value (32+ characters).')
os.environ.setdefault('PRODUCTION_SECRET_KEY', hashlib.sha512(render_secret.encode()).hexdigest())
os.environ.setdefault('PRODUCTION_DATA_ROOT', str(Path('/tmp/anadi-demo')))
os.environ.setdefault('PRODUCTION_CSRF_TRUSTED_ORIGINS', 'https://' + hostname)
from .production import *  # noqa: F403

if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
    raise ImproperlyConfigured('Render demo requires a PostgreSQL DATABASE_URL.')
if DATABASES['default']['OPTIONS']['sslmode'] == 'disable':
    raise ImproperlyConfigured('Render database connections require TLS.')
# Render terminates TLS and forwards its scheme; its edge controls this header.
# Waitress must preserve it (see scripts/render_start.py). Do not expose this
# configuration directly to the internet outside Render's managed ingress.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# Use the rightmost address appended by the managed ingress, never a spoofable
# first address supplied by the caller. Review this count if adding another proxy.
REST_FRAMEWORK = {**REST_FRAMEWORK, 'NUM_PROXIES': 1}
MIDDLEWARE = [MIDDLEWARE[0], 'whitenoise.middleware.WhiteNoiseMiddleware', *MIDDLEWARE[1:]]
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
            'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
# Upload functionality remains available for fictional demonstrations, but files
# on this free instance are explicitly temporary. No public upload route exists.
ALLOW_DEMO_SEED = True
SERVE_DEMO_BRANDING = True
