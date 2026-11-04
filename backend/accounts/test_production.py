import importlib
import os
import tempfile
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings


class ProductionConfigurationTests(SimpleTestCase):
    def test_postgres_url_decodes_credentials_and_rejects_invalid_urls(self):
        from config.database import postgres_database
        db = postgres_database('postgresql://demo:p%40ss@localhost:5433/demo_db?sslmode=disable')
        self.assertEqual(db['PASSWORD'], 'p@ss')
        self.assertEqual(db['PORT'], 5433)
        self.assertEqual(db['OPTIONS']['sslmode'], 'disable')
        for url in ('mysql://user:secret@localhost/db', 'postgresql://localhost/', 'invalid'):
            with self.assertRaises(ImproperlyConfigured) as error:
                postgres_database(url)
            self.assertNotIn('secret', str(error.exception))

    def load(self, **changes):
        values = {'PRODUCTION_SECRET_KEY': 'test-only-' + 'abcdefghijklmnopqrstuvwxyz0123456789' * 2,
                  'PRODUCTION_ALLOWED_HOSTS': 'api.example.test',
                  'PRODUCTION_CORS_ALLOWED_ORIGINS': 'https://example.test',
                  'PRODUCTION_CSRF_TRUSTED_ORIGINS': 'https://api.example.test',
                  'PRODUCTION_DATA_ROOT': tempfile.gettempdir(), 'PRODUCTION_HSTS_SECONDS': '3600'}
        values.update(changes)
        with patch.dict(os.environ, values):
            import sys
            sys.modules.pop('config.production', None)
            return importlib.import_module('config.production')

    def test_secure_defaults_and_shared_cache(self):
        settings = self.load()
        self.assertFalse(settings.DEBUG)
        self.assertTrue(settings.SECURE_SSL_REDIRECT)
        self.assertTrue(settings.SESSION_COOKIE_SECURE)
        self.assertTrue(settings.CSRF_COOKIE_SECURE)
        self.assertEqual(settings.CACHES['default']['BACKEND'], 'django.core.cache.backends.db.DatabaseCache')
        self.assertNotEqual(settings.PRIVATE_MEDIA_ROOT, settings.MEDIA_ROOT)
        self.assertIsNone(settings.SECURE_PROXY_SSL_HEADER)

    def test_invalid_production_values_fail_closed(self):
        for values in ({'PRODUCTION_SECRET_KEY': 'short'}, {'PRODUCTION_ALLOWED_HOSTS': '*'},
                       {'PRODUCTION_ALLOWED_HOSTS': ''}, {'PRODUCTION_CORS_ALLOWED_ORIGINS': 'http://example.test'},
                       {'PRODUCTION_CSRF_TRUSTED_ORIGINS': 'https://example.test/path'},
                       {'PRODUCTION_DATA_ROOT': 'relative/path'}, {'PRODUCTION_HSTS_SECONDS': '0'}):
            with self.subTest(values=values), self.assertRaises(ImproperlyConfigured):
                self.load(**values)

    def test_https_redirect_secure_response_and_cors(self):
        settings = self.load()
        with override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=True,
                               SECURE_HSTS_SECONDS=settings.SECURE_HSTS_SECONDS,
                               CORS_ALLOWED_ORIGINS=settings.CORS_ALLOWED_ORIGINS):
            self.assertEqual(self.client.get('/api/auth/me/').status_code, 301)
            response = self.client.get('/api/auth/me/', secure=True, HTTP_ORIGIN='https://example.test')
            self.assertEqual(response.status_code, 401)
            self.assertIn('max-age=3600', response['Strict-Transport-Security'])
            self.assertEqual(response['Access-Control-Allow-Origin'], 'https://example.test')
            spoof = self.client.get('/api/auth/me/', HTTP_X_FORWARDED_PROTO='https')
            self.assertEqual(spoof.status_code, 301)
