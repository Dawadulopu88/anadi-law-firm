from io import StringIO

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from .admin import ClientAdmin
from .models import Client
from .serializers import StaffClientSerializer
from .views import ClientViewSet

User = get_user_model()


class ClientAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_user(username='admin_role', role='admin')
        cls.lawyer = User.objects.create_user(username='lawyer', role='lawyer')
        cls.staff = User.objects.create_user(username='staff', role='staff')
        cls.user_one = User.objects.create_user(username='client_one', role='client')
        cls.user_two = User.objects.create_user(username='client_two', role='client')
        cls.unlinked = User.objects.create_user(username='unlinked_client', role='client')
        cls.one = Client.objects.create(
            user=cls.user_one, full_name='Client One', created_by=cls.admin_user,
            notes='Secret internal note', nid_or_reference='Private ID',
        )
        cls.two = Client.objects.create(user=cls.user_two, full_name='Client Two', created_by=cls.admin_user)
        cls.walk_in = Client.objects.create(full_name='No login yet', created_by=cls.admin_user)

    def setUp(self):
        self.api = APIClient()

    def detail(self, record=None):
        return f'/api/clients/{(record or self.one).pk}/'

    def test_anonymous_cannot_list_read_or_write(self):
        for method, url in [('get', '/api/clients/'), ('get', self.detail()), ('post', '/api/clients/'), ('patch', self.detail())]:
            with self.subTest(method=method):
                response = getattr(self.api, method)(url) if method == 'get' else getattr(self.api, method)(url, {}, format='json')
                self.assertEqual(response.status_code, 401)

    def test_all_firm_roles_can_list_create_read_and_update(self):
        for actor in [self.admin_user, self.lawyer, self.staff]:
            with self.subTest(role=actor.role):
                self.api.force_authenticate(actor)
                listed = self.api.get('/api/clients/')
                self.assertEqual(listed.status_code, 200)
                self.assertGreaterEqual(listed.data['count'], 3)
                response = self.api.post('/api/clients/', {'full_name': 'Sample ' + actor.role}, format='json')
                self.assertEqual(response.status_code, 201)
                record = Client.objects.get(pk=response.data['id'])
                self.assertEqual(record.created_by, actor)
                self.assertIsNone(record.user)
                self.assertEqual(self.api.get(self.detail(record)).status_code, 200)
                self.assertEqual(self.api.patch(self.detail(record), {'phone': '123'}, format='json').status_code, 200)

    def test_firm_can_see_internal_fields(self):
        self.api.force_authenticate(self.staff)
        data = self.api.get(self.detail()).data
        self.assertEqual(data['notes'], 'Secret internal note')
        self.assertEqual(data['nid_or_reference'], 'Private ID')

    def test_client_sees_only_own_list_and_record(self):
        self.api.force_authenticate(self.user_one)
        response = self.api.get('/api/clients/')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.one.pk)
        self.assertEqual(self.api.get(self.detail()).status_code, 200)

    def test_client_cannot_discover_other_or_unlinked_records(self):
        self.api.force_authenticate(self.user_one)
        for url in [self.detail(self.two), self.detail(self.walk_in), '/api/clients/999999/']:
            self.assertEqual(self.api.get(url).status_code, 404)
        # Untrusted query parameters must never override queryset ownership.
        response = self.api.get(f'/api/clients/?user={self.user_two.pk}')
        self.assertEqual([item['id'] for item in response.data['results']], [self.one.pk])

    def test_client_response_excludes_internal_fields_in_list_and_detail(self):
        self.api.force_authenticate(self.user_one)
        for data in [self.api.get(self.detail()).data, self.api.get('/api/clients/').data['results'][0]]:
            self.assertEqual(set(data), {'id', 'full_name', 'phone', 'email', 'address', 'status', 'assigned_lawyer_name', 'created_at', 'updated_at'})
            self.assertNotIn('Secret internal note', str(data))
            self.assertNotIn('Private ID', str(data))

    def test_client_cannot_write_even_own_record(self):
        self.api.force_authenticate(self.user_one)
        self.assertEqual(self.api.post('/api/clients/', {'full_name': 'New'}, format='json').status_code, 403)
        for method in ['put', 'patch', 'delete']:
            self.assertEqual(getattr(self.api, method)(self.detail(), {'full_name': 'Changed'}, format='json').status_code, 403)
        self.one.refresh_from_db()
        self.assertEqual(self.one.full_name, 'Client One')

    def test_client_without_profile_gets_empty_list(self):
        self.api.force_authenticate(self.unlinked)
        self.assertEqual(self.api.get('/api/clients/').data['count'], 0)
        self.assertEqual(self.api.get(self.detail()).status_code, 404)

    def test_invalid_role_has_no_client_access(self):
        user = User.objects.create_user(username='unknown', role='unknown')
        self.api.force_authenticate(user)
        self.assertEqual(self.api.get('/api/clients/').status_code, 403)

    def test_no_delete_endpoint_for_firm_members(self):
        self.api.force_authenticate(self.admin_user)
        self.assertEqual(self.api.delete(self.detail()).status_code, 405)
        self.assertTrue(Client.objects.filter(pk=self.one.pk).exists())

    def test_status_can_archive_without_deleting(self):
        self.api.force_authenticate(self.staff)
        response = self.api.patch(self.detail(), {'status': 'archived'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.one.refresh_from_db()
        self.assertEqual(self.one.status, 'archived')

    def test_forged_creator_is_ignored_and_original_creator_is_immutable(self):
        self.api.force_authenticate(self.staff)
        response = self.api.post('/api/clients/', {'full_name': 'Created', 'created_by': self.user_two.pk}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['created_by'], self.staff.pk)
        response = self.api.patch(self.detail(), {'created_by': self.staff.pk}, format='json')
        self.assertEqual(response.status_code, 200)
        self.one.refresh_from_db()
        self.assertEqual(self.one.created_by, self.admin_user)

    def test_invalid_client_fields_are_rejected(self):
        self.api.force_authenticate(self.staff)
        for payload in [{'full_name': ''}, {'full_name': 'X', 'email': 'not-email'}, {'full_name': 'X', 'status': 'unknown'}]:
            self.assertEqual(self.api.post('/api/clients/', payload, format='json').status_code, 400)

    def test_account_links_require_existing_active_client_role(self):
        self.api.force_authenticate(self.staff)
        inactive = User.objects.create_user(username='inactive_client', role='client', is_active=False)
        for user_id in [self.admin_user.pk, self.lawyer.pk, self.staff.pk, inactive.pk, 999999]:
            response = self.api.post('/api/clients/', {'full_name': 'X', 'user': user_id}, format='json')
            self.assertEqual(response.status_code, 400)

    def test_duplicate_account_links_return_validation_errors(self):
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.api.post('/api/clients/', {'full_name': 'Duplicate', 'user': self.user_one.pk}, format='json').status_code, 400)
        self.assertEqual(self.api.patch(self.detail(self.two), {'user': self.user_one.pk}, format='json').status_code, 400)
        self.assertEqual(self.api.patch(self.detail(), {'user': self.user_one.pk}, format='json').status_code, 200)

    def test_link_unlink_and_relink_change_access_immediately(self):
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.api.patch(self.detail(self.walk_in), {'user': self.unlinked.pk}, format='json').status_code, 200)
        self.api.force_authenticate(self.unlinked)
        self.assertEqual(self.api.get(self.detail(self.walk_in)).status_code, 200)
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.api.patch(self.detail(self.walk_in), {'user': None}, format='json').status_code, 200)
        self.api.force_authenticate(self.unlinked)
        self.assertEqual(self.api.get(self.detail(self.walk_in)).status_code, 404)

    def test_pagination(self):
        Client.objects.bulk_create([Client(full_name=f'Sample {i}', created_by=self.admin_user) for i in range(20)])
        self.api.force_authenticate(self.staff)
        data = self.api.get('/api/clients/').data
        self.assertEqual(data['count'], 23)
        self.assertEqual(len(data['results']), 20)
        self.assertIsNotNone(data['next'])

    def test_bangla_client_name_round_trip(self):
        self.api.force_authenticate(self.staff)
        response = self.api.post('/api/clients/', {'full_name': 'নমুনা মক্কেল'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Client.objects.get(pk=response.data['id']).full_name, 'নমুনা মক্কেল')

    def test_real_jwt_obeys_database_role_changes(self):
        password = 'Test-jwt-client-579!'
        self.staff.set_password(password)
        self.staff.save()
        response = self.api.post('/api/auth/token/', {'username': self.staff.username, 'password': password}, format='json')
        self.assertEqual(response.status_code, 200)
        self.api.credentials(HTTP_AUTHORIZATION='Bearer ' + response.data['access'])
        self.assertEqual(self.api.get('/api/clients/').status_code, 200)
        self.staff.role = 'client'
        self.staff.save(update_fields=['role'])
        self.assertEqual(self.api.get('/api/clients/').data['count'], 0)
        self.assertEqual(self.api.post('/api/clients/', {'full_name': 'No'}, format='json').status_code, 403)

    def test_database_enforces_unique_user_link(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Client.objects.create(user=self.user_one, full_name='Duplicate', created_by=self.staff)

    def test_link_race_is_reported_as_validation_error(self):
        serializer = StaffClientSerializer(data={'user': self.unlinked.pk, 'full_name': 'Racing'})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        Client.objects.create(user=self.unlinked, full_name='Won race', created_by=self.staff)
        with self.assertRaises(ValidationError):
            ClientViewSet().save_client(serializer, created_by=self.staff)


class ClientAdminTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_superuser(username='admin', password='test-admin-password')
        self.model_admin = ClientAdmin(Client, admin.site)
        self.request = RequestFactory().get('/admin/clients/client/')
        self.request.user = self.actor

    def test_admin_create_sets_creator_and_update_preserves_it(self):
        obj = Client(full_name='Admin-created')
        self.model_admin.save_model(self.request, obj, None, False)
        self.assertEqual(obj.created_by, self.actor)
        other = User.objects.create_superuser(username='other_admin', password='test-other-password')
        self.request.user = other
        obj.full_name = 'Updated'
        self.model_admin.save_model(self.request, obj, None, True)
        obj.refresh_from_db()
        self.assertEqual(obj.created_by, self.actor)

    def test_client_role_cannot_use_admin_even_with_staff_flag_and_model_permissions(self):
        user = User.objects.create_user(username='client_with_flags', role='client', is_staff=True)
        user.user_permissions.set(Permission.objects.filter(content_type__app_label='clients'))
        self.client.force_login(user)
        for url in ['/admin/clients/client/', '/admin/clients/client/add/']:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_admin_list_and_add_pages_render(self):
        self.client.force_login(self.actor)
        self.assertEqual(self.client.get('/admin/clients/client/').status_code, 200)
        self.assertEqual(self.client.get('/admin/clients/client/add/').status_code, 200)

    def test_admin_deletion_is_disabled(self):
        self.assertFalse(self.model_admin.has_delete_permission(self.request))

    def test_model_validation_rejects_nonclient_user(self):
        with self.assertRaises(DjangoValidationError):
            Client(full_name='Invalid', user=self.actor, created_by=self.actor).full_clean()

    def test_existing_record_remains_editable_after_login_is_deactivated(self):
        user = User.objects.create_user(username='former_login', role='client')
        record = Client.objects.create(full_name='Existing', user=user, created_by=self.actor)
        user.is_active = False
        user.save(update_fields=['is_active'])
        record.status = 'archived'
        record.full_clean()
        record.save()
        self.assertEqual(record.status, 'archived')
        with self.assertRaises(DjangoValidationError):
            Client(full_name='New', user=user, created_by=self.actor).full_clean()


class SeedStage3Tests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user(username='demo_owner', role='admin')

    def seed(self):
        call_command('seed_stage3', created_by='demo_owner', stdout=StringIO())

    def test_repeatable_seed_has_no_fixed_passwords(self):
        self.seed()
        self.seed()
        self.assertEqual(Client.objects.count(), 2)
        users = User.objects.filter(username__startswith='stage3_demo_')
        self.assertEqual(users.count(), 4)
        self.assertTrue(all(not user.has_usable_password() for user in users))
        self.assertTrue(all(record.created_by == self.actor for record in Client.objects.all()))

    def test_seed_preserves_edited_client(self):
        self.seed()
        obj = Client.objects.first()
        obj.full_name = 'Edited name'
        obj.save()
        self.seed()
        obj.refresh_from_db()
        self.assertEqual(obj.full_name, 'Edited name')

    def test_seed_requires_active_firm_creator(self):
        self.actor.role = 'client'
        self.actor.save()
        with self.assertRaises(CommandError):
            self.seed()
        self.assertEqual(Client.objects.count(), 0)

    def test_seed_conflict_rolls_back(self):
        User.objects.create_user(username='stage3_demo_client_two', role='lawyer')
        with self.assertRaises(CommandError):
            self.seed()
        self.assertEqual(Client.objects.count(), 0)
        self.assertFalse(User.objects.filter(username='stage3_demo_staff').exists())
