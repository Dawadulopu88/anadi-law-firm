from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from .permissions import (
    IsAdmin, IsLawyer, IsStaff, IsClient, IsFirmMember,
    IsFirmMemberOrClientReadOnly, has_role, is_firm_member,
)

User = get_user_model()


class RolePermissionTests(SimpleTestCase):
    def user(self, role, active=True):
        return SimpleNamespace(is_authenticated=True, is_active=active, role=role, pk=10)

    def test_each_role_permission_accepts_only_its_role(self):
        for permission, expected in [(IsAdmin, 'admin'), (IsLawyer, 'lawyer'), (IsStaff, 'staff'), (IsClient, 'client')]:
            for role in ['admin', 'lawyer', 'staff', 'client', 'unknown']:
                with self.subTest(permission=permission.__name__, role=role):
                    request = SimpleNamespace(user=self.user(role), method='GET')
                    self.assertEqual(permission().has_permission(request, None), role == expected)

    def test_firm_membership(self):
        for role in ['admin', 'lawyer', 'staff', 'client', 'unknown']:
            request = SimpleNamespace(user=self.user(role))
            self.assertEqual(IsFirmMember().has_permission(request, None), role in ['admin', 'lawyer', 'staff'])

    def test_anonymous_inactive_and_unrecognized_users_fail_closed(self):
        for user in [AnonymousUser(), None, self.user('admin', active=False), self.user('unknown')]:
            self.assertFalse(is_firm_member(user))
        self.assertFalse(has_role(self.user('client', active=False), 'client'))

    def test_superuser_flag_does_not_bypass_application_role(self):
        user = self.user('client')
        user.is_superuser = True
        self.assertFalse(is_firm_member(user))

    def test_client_object_permission_checks_owner_and_read_only(self):
        permission = IsFirmMemberOrClientReadOnly()
        request = SimpleNamespace(user=self.user('client'), method='GET')
        self.assertTrue(permission.has_object_permission(request, None, SimpleNamespace(user_id=10)))
        self.assertFalse(permission.has_object_permission(request, None, SimpleNamespace(user_id=20)))
        request.method = 'PATCH'
        self.assertFalse(permission.has_permission(request, None))
        self.assertFalse(permission.has_object_permission(request, None, SimpleNamespace(user_id=10)))


class CurrentUserTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = 'Local-test-password-349!'
        cls.user = User.objects.create_user(
            username='client_me', password=cls.password, role='client',
            first_name='Test', last_name='Client', email='test@example.test', phone='123',
        )

    def setUp(self):
        self.api = APIClient()

    def login(self):
        response = self.api.post('/api/auth/token/', {
            'username': self.user.username, 'password': self.password,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.api.credentials(HTTP_AUTHORIZATION='Bearer ' + response.data['access'])

    def test_anonymous_and_invalid_tokens_rejected(self):
        self.assertEqual(self.api.get('/api/auth/me/').status_code, 401)
        self.api.credentials(HTTP_AUTHORIZATION='Bearer invalid')
        self.assertEqual(self.api.get('/api/auth/me/').status_code, 401)

    def test_jwt_returns_only_current_users_safe_fields(self):
        self.login()
        response = self.api.get('/api/auth/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {'id', 'username', 'first_name', 'last_name', 'email', 'phone', 'role'})
        self.assertEqual(response.data['id'], self.user.pk)
        self.assertEqual(response.data['role'], 'client')

    def test_current_user_endpoint_cannot_escalate_role_or_update_profile(self):
        self.login()
        for method in ['post', 'put', 'patch', 'delete']:
            self.assertEqual(getattr(self.api, method)('/api/auth/me/', {'role': 'admin'}, format='json').status_code, 405)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'client')

    def test_existing_jwt_uses_current_database_role(self):
        self.login()
        self.user.role = 'staff'
        self.user.save(update_fields=['role'])
        self.assertEqual(self.api.get('/api/auth/me/').data['role'], 'staff')

    def test_deactivated_user_cannot_use_existing_access_token(self):
        self.login()
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        self.assertEqual(self.api.get('/api/auth/me/').status_code, 401)
