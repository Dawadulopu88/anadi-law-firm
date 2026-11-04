"""Stage 11: real JWT workflow and a route-discovered role/method matrix."""
import re
import tempfile
from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import URLResolver, get_resolver
from django.utils import timezone
from rest_framework.test import APIClient

from firm.models import PracticeArea

User = get_user_model()
ROLES = ('anonymous', 'client', 'staff', 'lawyer', 'admin')


def api_routes(patterns=None, prefix=''):
    """Discover all canonical API routes, excluding equivalent format suffixes."""
    for item in (get_resolver().url_patterns if patterns is None else patterns):
        route = prefix + str(item.pattern)
        if isinstance(item, URLResolver):
            yield from api_routes(item.url_patterns, route)
        elif route.startswith('api/') and '(?P<format>' not in route and 'drf_format_suffix' not in route:
            route = route.replace('^', '').rstrip('$')
            route = re.sub(r'\(\?P<(\w+)>[^)]+\)', r'<\1>', route)
            route = re.sub(r'<(?:int|str|slug):([^>]+)>', r'<\1>', route)
            callback = item.callback
            actions = getattr(callback, 'actions', None)
            methods = actions if actions is not None else {
                method: method for method in callback.cls.http_method_names
                if hasattr(callback.cls, method)
            }
            for method, action in methods.items():
                if method not in ('head', 'options') and method in callback.cls.http_method_names:
                    yield '/' + route, method, action


def allowed_roles(route, method):
    """Independent access contract, rather than introspection of permission classes."""
    root = route.split('/')[2]
    if root in ('firm', 'practice-areas', 'lawyers', 'jurisdictions', 'rights-topics',
                'articles', 'faqs', 'knowledge', 'help-contacts', 'guided-flows',
                'guided-questions', 'guided-options', 'pathways', 'courses', 'live-sessions',
                'session-registrations'):
        return ROLES
    if route.startswith('/api/auth/token/') or route.startswith('/api/legal-aid/apply/') or route.startswith('/api/legal-aid/track/'):
        return ROLES
    if route == '/api/consultations/' and method == 'post':
        return ROLES
    if root == 'portal':
        return ('client',)
    if root in ('consultations', 'tasks', 'payments', 'legal-aid'):
        return ('staff', 'lawyer', 'admin')
    if root == 'case-assignments':
        return ('staff', 'lawyer', 'admin') if method == 'get' else ('staff', 'admin')
    if root == 'cases' and method == 'post':
        return ('staff', 'admin')
    if root in ('clients', 'appointments', 'cases', 'case-notes', 'hearings', 'documents', 'invoices'):
        return ('client', 'staff', 'lawyer', 'admin') if method == 'get' else ('staff', 'lawyer', 'admin')
    if root == 'users':
        return ('staff', 'lawyer', 'admin') if method == 'get' else ('admin',)
    if route in ('/api/', '/api/auth/me/', '/api/auth/change-password/'):
        return ('client', 'staff', 'lawyer', 'admin')
    raise AssertionError(f'New route needs an explicit access contract: {route}')


class IntegrationFixtures(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = 'Integration-demo-only-738!'
        cls.users = {role: User.objects.create_user(username=f'integration_{role}', role=role, password=cls.password)
                     for role in ROLES if role != 'anonymous'}
        cls.other = User.objects.create_user(username='other_client', password=cls.password)
        cls.area = PracticeArea.objects.create(name='Sample', slug='integration-sample')

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.api = APIClient()

    def login(self, user):
        self.api.credentials()
        response = self.api.post('/api/auth/token/', {'username': user.username, 'password': self.password}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.api.credentials(HTTP_AUTHORIZATION='Bearer ' + response.data['access'])

    def post(self, path, payload, expected=201, format='json'):
        response = self.api.post(path, payload, format=format)
        self.assertEqual(response.status_code, expected, response.data)
        return response.data


class PermissionMatrixTests(IntegrationFixtures):
    def test_every_canonical_api_route_and_method_for_five_roles(self):
        routes = sorted(set(api_routes()))
        self.assertGreater(len(routes), 80)
        for role in ROLES:
            if role != 'anonymous':
                self.login(self.users[role])
            for route, method, action in routes:
                cache.clear()  # Rate limiting is tested separately, not bypassed in production.
                url = re.sub(r'<[^>]+>', '999999', route)
                if route == '/api/knowledge/search/':
                    url += '?q=sample'
                with self.subTest(role=role, route=route, method=method):
                    response = getattr(self.api, method)(url, {}, format='json')
                    if role not in allowed_roles(route, method):
                        self.assertEqual(response.status_code, 401 if role == 'anonymous' else 403)
                    else:
                        # Empty writes must validate; missing objects must return 404.
                        # These are access gates, not substitutes for real-object tests.
                        self.assertIn(response.status_code, (200, 400, 404), getattr(response, 'data', None))


class FullWorkflowTests(IntegrationFixtures):
    def test_visitor_to_paid_client_portal_using_only_business_apis(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(PRIVATE_MEDIA_ROOT=Path(directory)):
            inquiry = self.post('/api/consultations/', {'name': 'Sample visitor', 'phone': '01700000000',
                'email': 'demo@example.test', 'practice_area': self.area.pk, 'message': 'Sample request', 'preferred_language': 'bn'})
            self.login(self.users['staff'])
            converted = self.post(f"/api/consultations/{inquiry['id']}/convert/", {})
            client_id = converted['client_id']
            repeat = self.post(f"/api/consultations/{inquiry['id']}/convert/", {}, 200)
            self.assertEqual(repeat['client_id'], client_id)
            linked = self.api.patch(f'/api/clients/{client_id}/', {'user': self.users['client'].pk}, format='json')
            self.assertEqual(linked.status_code, 200)
            case = self.post('/api/cases/', {'case_number': 'INTEGRATION-1', 'title': 'Sample case', 'client': client_id,
                'practice_area': self.area.pk, 'court': 'Demo court', 'opposite_party': 'Demo opposing party', 'priority': 'high'})
            case_id = case['id']
            assignment = self.post('/api/case-assignments/', {'case': case_id, 'user': self.users['lawyer'].pk, 'role': 'lead'})
            self.post('/api/case-assignments/', {'case': case_id, 'user': self.users['staff'].pk, 'role': 'support'})
            self.login(self.users['lawyer'])
            self.post('/api/case-notes/', {'case': case_id, 'body': 'Internal strategy', 'is_internal': True})
            self.post('/api/case-notes/', {'case': case_id, 'body': 'Shared update', 'is_internal': False})
            start = timezone.now() + timedelta(days=7)
            self.post('/api/hearings/', {'case': case_id, 'court_name': 'Demo court', 'hearing_at': start.isoformat(), 'notes': 'Internal hearing detail'})
            self.post('/api/tasks/', {'case': case_id, 'title': 'Prepare documents', 'assigned_to': self.users['lawyer'].pk, 'due_date': start.date().isoformat()})
            self.post('/api/appointments/', {'case': case_id, 'client': client_id, 'lawyer': self.users['lawyer'].pk,
                'start': start.isoformat(), 'end': (start + timedelta(hours=1)).isoformat(), 'appointment_type': 'consultation'})
            document = self.post('/api/documents/', {'case': case_id, 'title': 'Private sample', 'document_type': 'sample',
                'file': SimpleUploadedFile('sample.txt', b'Sample private content', content_type='text/plain')}, format='multipart')
            invoice = self.post('/api/invoices/', {'invoice_number': 'INT-INV-1', 'client': client_id, 'case': case_id,
                'issue_date': timezone.localdate().isoformat(), 'due_date': start.date().isoformat(), 'amount': '100.00'})
            for amount in ('40.00', '60.00'):
                self.post('/api/payments/', {'invoice': invoice['id'], 'amount': amount, 'method': 'cash', 'date': timezone.localdate().isoformat()})
            self.login(self.users['client'])
            self.assertEqual(self.api.get(f"/api/documents/{document['id']}/download/").status_code, 404)
            self.assertEqual(self.api.get('/api/portal/documents/').data['count'], 0)
            self.assertEqual(self.api.get('/api/case-notes/').data['results'][0]['body'], 'Shared update')
            self.assertEqual(self.api.get('/api/case-notes/').data['count'], 1)
            own_case = self.api.get('/api/portal/cases/').data['results'][0]
            self.assertEqual(own_case['lead_lawyers'][0]['id'], self.users['lawyer'].pk)
            self.assertNotIn('opposite_party', own_case)
            self.assertNotIn('notes', self.api.get('/api/portal/hearings/').data['results'][0])
            self.assertEqual(self.api.get('/api/portal/invoices/').data['results'][0]['status'], 'paid')
            self.assertEqual(self.api.get('/api/portal/summary/').data['outstanding_balance'], '0.00')
            self.login(self.users['staff'])
            self.assertEqual(self.api.patch(f"/api/documents/{document['id']}/", {'is_client_visible': True}, format='json').status_code, 200)
            self.login(self.users['client'])
            downloaded = self.api.get(f"/api/documents/{document['id']}/download/")
            self.assertEqual(downloaded.status_code, 200)
            self.assertEqual(b''.join(downloaded.streaming_content), b'Sample private content')
            self.assertIn('no-store', downloaded['Cache-Control'])
            self.login(self.other)
            for path in ('cases', 'documents', 'invoices'):
                self.assertEqual(self.api.get(f'/api/portal/{path}/').data['count'], 0)
            for path, pk in [('cases', case_id), ('documents', document['id']), ('invoices', invoice['id'])]:
                self.assertEqual(self.api.get(f'/api/{path}/{pk}/').status_code, 404)
            self.assertEqual(self.api.get(f"/api/documents/{document['id']}/download/").status_code, 404)
            self.login(self.users['staff'])
            self.assertEqual(self.api.delete(f"/api/case-assignments/{assignment['id']}/").status_code, 204)
            self.login(self.users['lawyer'])
            self.assertEqual(self.api.get(f'/api/cases/{case_id}/').status_code, 404)
            self.assertEqual(self.api.get(f"/api/documents/{document['id']}/download/").status_code, 404)


class SecurityChecks(IntegrationFixtures):
    def test_account_admin_rejects_non_admin_roles_even_with_superuser_flag(self):
        for role in ('client', 'lawyer', 'staff'):
            user = self.users[role]
            user.is_staff = user.is_superuser = True
            user.save()
            self.client.force_login(user)
            for path in ('/admin/accounts/user/', '/admin/accounts/user/add/',
                         f'/admin/accounts/user/{user.pk}/change/', f'/admin/accounts/user/{user.pk}/delete/'):
                self.assertEqual(self.client.get(path).status_code, 403)

    def test_password_validation_rejects_common_short_and_numeric_passwords(self):
        for value in ('123', 'password', '123456789123'):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_password(value, self.users['client'])

    def test_token_endpoints_share_an_ip_rate_limit(self):
        for _ in range(20):
            self.assertEqual(self.api.post('/api/auth/token/', {}, format='json').status_code, 400)
        self.assertEqual(self.api.post('/api/auth/token/refresh/', {}, format='json').status_code, 429)

    def test_all_public_submission_routes_are_rate_limited(self):
        for route in ('consultations', 'legal-aid/apply', 'session-registrations'):
            cache.clear()
            for _ in range(5):
                self.assertEqual(self.api.post(f'/api/{route}/', {}, format='json').status_code, 400)
            self.assertEqual(self.api.post(f'/api/{route}/', {}, format='json').status_code, 429)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'])
    def test_non_debug_errors_and_private_paths_do_not_expose_details(self):
        for path in ('/private_media/secret.txt', '/media/secret.txt', '/missing/'):
            response = self.api.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertNotIn(b'Traceback', response.content)
            self.assertNotIn(b'SECRET_KEY', response.content)

    def test_inactive_user_token_is_rejected(self):
        self.login(self.users['client'])
        user = self.users['client']
        user.is_active = False
        user.save(update_fields=['is_active'])
        self.assertEqual(self.api.get('/api/portal/summary/').status_code, 401)
