"""Shared Django settings for the Anadi Law Firm API."""
from datetime import timedelta
from pathlib import Path

from decouple import AutoConfig, Csv
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent
config = AutoConfig(search_path=BASE_DIR)
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'corsheaders', 'accounts', 'firm', 'clients', 'intake', 'cases', 'knowledge', 'documents',
    'billing', 'legalaid', 'academy',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': config('DB_NAME', default='lawfirm_db'),
    'USER': config('DB_USER', default='lawfirm_user'),
    'PASSWORD': config('DB_PASSWORD', default=''),
    'HOST': config('DB_HOST', default='127.0.0.1'),
    'PORT': config('DB_PORT', default='3306'),
    'OPTIONS': {
        'charset': 'utf8mb4',
        'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
    },
}}
if config('USE_SQLITE', default=False, cast=bool):
    # Zero-setup local development option. Use MySQL/PostgreSQL for shared or hosted data.
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
if config('DATABASE_URL', default=''):
    from .database import postgres_database
    DATABASES = {'default': postgres_database(config('DATABASE_URL'))}
AUTH_USER_MODEL = 'accounts.User'
# Preserve the primary-key type in the existing initial migration.
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.JSONRenderer',),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    # Local/direct deployments identify callers by their actual socket address.
    # Configure trusted proxy handling explicitly when deploying behind a proxy.
    'NUM_PROXIES': 0,
    'DEFAULT_THROTTLE_RATES': {
        'token_burst': '20/min',
        'public_form_burst': '5/min',
        'public_form_daily': '30/day',
        'public_tracking': '100/hour',
        'consultation_burst': '5/min',
        'consultation_daily': '30/day',
    },
}
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5500,http://127.0.0.1:5500,http://localhost:5173,http://127.0.0.1:5173',
    cast=Csv(),
)
CORS_URLS_REGEX = r'^/api/.*$'
# Lets the browser frontend read the download filename of protected documents.
CORS_EXPOSE_HEADERS = ['Content-Disposition']
LANGUAGE_CODE = 'en'
LANGUAGES = [('en', _('English')), ('bn', _('Bangla'))]
LOCALE_PATHS = [BASE_DIR / 'locale']
TIME_ZONE = 'Asia/Dhaka'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Public branding only; confidential uploads must use PRIVATE_MEDIA_ROOT.
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
PRIVATE_MEDIA_ROOT = BASE_DIR / 'private_media'
# DEBUG URL routes serve public branding only; private files remain unexposed.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
