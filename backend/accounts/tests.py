from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import path, reverse
from rest_framework.test import APIClient
from rest_framework.views import APIView
from rest_framework.response import Response

from config.urls import urlpatterns as project_urls

User = get_user_model()


class ProtectedProbe(APIView):
    def get(self, request):
        return Response({'username': request.user.username})


# Test-only route exercises the actual API defaults.
urlpatterns = [*project_urls, path('api/test-protected/', ProtectedProbe.as_view())]


@override_settings(ROOT_URLCONF=__name__)
class FoundationSettingsTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_api_denies_anonymous_requests_by_default(self):
        self.assertEqual(self.client.get('/api/test-protected/').status_code, 401)

    def test_bangla_language_negotiation(self):
        response = self.client.get('/api/test-protected/', HTTP_ACCEPT_LANGUAGE='bn')
        self.assertEqual(response.headers['Content-Language'], 'bn')

    @override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:5500'])
    def test_cors_only_allows_configured_frontend(self):
        for origin, allowed in [('http://localhost:5500', True), ('https://untrusted.example', False)]:
            with self.subTest(origin=origin):
                response = self.client.options(
                    '/api/auth/token/', HTTP_ORIGIN=origin,
                    HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
                    HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization,content-type',
                )
                self.assertEqual('Access-Control-Allow-Origin' in response.headers, allowed)
                if allowed:
                    self.assertEqual(response.headers['Access-Control-Allow-Origin'], origin)

    def test_upload_directories_have_no_public_routes(self):
        for url in ['/media/confidential.pdf', '/private_media/confidential.pdf']:
            self.assertEqual(self.client.get(url).status_code, 404)


@override_settings(ROOT_URLCONF=__name__)
class AuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = 'Test-only-strong-password-428!'
        cls.user = User.objects.create_user(username='client_demo', password=cls.password)

    def setUp(self):
        self.client = APIClient()

    def test_login_refresh_and_authenticated_request(self):
        response = self.client.post(reverse('token_obtain'), {
            'username': self.user.username, 'password': self.password,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        protected = self.client.get('/api/test-protected/')
        self.assertEqual(protected.status_code, 200)
        self.assertEqual(protected.data['username'], self.user.username)
        self.client.credentials()
        refreshed = self.client.post(reverse('token_refresh'), {'refresh': response.data['refresh']}, format='json')
        self.assertEqual(refreshed.status_code, 200)
        self.assertIn('access', refreshed.data)

    def test_wrong_password_and_inactive_user_are_rejected(self):
        response = self.client.post(reverse('token_obtain'), {
            'username': self.user.username, 'password': 'incorrect',
        }, format='json')
        self.assertEqual(response.status_code, 401)
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        response = self.client.post(reverse('token_obtain'), {
            'username': self.user.username, 'password': self.password,
        }, format='json')
        self.assertEqual(response.status_code, 401)

    def test_invalid_refresh_token_is_rejected(self):
        response = self.client.post(reverse('token_refresh'), {'refresh': 'invalid'}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_regular_users_default_to_client(self):
        self.assertEqual(self.user.role, User.Role.CLIENT)
        self.assertFalse(self.user.is_staff)

    def test_superuser_receives_admin_role(self):
        user = User.objects.create_superuser(username='admin_demo', password=self.password)
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_superuser_cannot_have_client_role(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(username='invalid_admin', password=self.password, role='client')
