import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from billing.models import Invoice
from cases.models import Case
from clients.models import Client
from documents.models import Document
from knowledge.models import KnowledgeArticle

User = get_user_model()


@override_settings(DEBUG=True)
class DemoSeedTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='seed_admin', password='Test-demo-only-867!')
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.override = override_settings(PRIVATE_MEDIA_ROOT=Path(self.directory.name))
        self.override.enable()
        self.addCleanup(self.override.disable)

    def seed(self):
        output = StringIO()
        call_command('seed_demo', created_by=self.admin.username, stdout=output)
        return output.getvalue()

    def counts(self):
        return {model._meta.label: model.objects.count() for model in apps.get_models()
                if model._meta.app_label in ('accounts', 'firm', 'clients', 'intake', 'cases', 'documents', 'billing', 'legalaid', 'knowledge', 'academy')}

    def test_complete_seed_is_repeatable_and_preserves_edits_and_passwords(self):
        self.seed()
        first = self.counts()
        owner = User.objects.get(username='stage3_demo_client_one')
        self.assertFalse(owner.has_usable_password())
        owner.set_password('Chosen-demo-password-751!')
        owner.save()
        original_hash = owner.password
        case = Case.objects.get(case_number='DEMO-12-001')
        case.title = 'Locally edited title'
        case.save()
        self.seed()
        self.assertEqual(self.counts(), first)
        owner.refresh_from_db()
        self.assertEqual(owner.password, original_hash)
        case.refresh_from_db()
        self.assertEqual(case.title, 'Locally edited title')
        self.assertEqual(case.assignments.filter(role='lead', user__role='lawyer').count(), 1)
        self.assertEqual(Invoice.objects.get(invoice_number='DEMO-12-INV-001').balance, 60)
        self.assertFalse(KnowledgeArticle.objects.exclude(status='draft').exists())
        self.assertEqual(len(list(Path(self.directory.name).rglob('*.txt'))), 1)

    def test_seeded_client_portal_and_private_document_scope(self):
        self.seed()
        api = APIClient()
        for username, expected_cases in [('stage3_demo_client_one', 1), ('stage3_demo_client_two', 1)]:
            api.force_authenticate(User.objects.get(username=username))
            self.assertEqual(api.get('/api/portal/cases/').data['count'], expected_cases)
            self.assertEqual(api.get('/api/portal/documents/').data['count'], 0)
        api.force_authenticate(User.objects.get(username='stage3_demo_client_one'))
        self.assertEqual(api.get('/api/portal/summary/').data['outstanding_balance'], '60.00')
        document = Document.objects.get(title='Stage 12 private sample')
        self.assertEqual(api.get(f'/api/documents/{document.pk}/download/').status_code, 404)

    @override_settings(DEBUG=False)
    def test_non_development_seed_is_rejected(self):
        with self.assertRaises(CommandError):
            self.seed()
        self.assertEqual(Case.objects.count(), 0)

    def test_invalid_actor_and_conflicting_demo_username_roll_back(self):
        with self.assertRaises(CommandError):
            call_command('seed_demo', created_by='missing', stdout=StringIO())
        User.objects.create_user(username='stage3_demo_client_one', role='staff')
        before = self.counts()
        with self.assertRaises(CommandError):
            self.seed()
        self.assertEqual(self.counts(), before)

    def test_failure_after_file_write_removes_file_and_database_records(self):
        before = self.counts()
        with patch('accounts.management.commands.seed_demo.Payment.objects.get_or_create', side_effect=CommandError('Simulated failure')):
            with self.assertRaises(CommandError):
                self.seed()
        self.assertEqual(self.counts(), before)
        self.assertFalse(any(path.is_file() for path in Path(self.directory.name).rglob('*')))


class StaffSelectorTests(TestCase):
    def test_lawyer_selectors_work_without_user_admin_permission(self):
        staff = User.objects.create_user(username='selector_staff', role='staff', is_staff=True)
        staff.user_permissions.add(*Permission.objects.filter(codename__in=['add_appointment', 'add_lawyerprofile']))
        lawyer = User.objects.create_user(username='selectable_lawyer', role='lawyer')
        self.client.force_login(staff)
        for route, field in [('/admin/intake/appointment/add/', 'lawyer'), ('/admin/firm/lawyerprofile/add/', 'user')]:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200)
            form = response.context['adminform'].form
            self.assertIn(lawyer, form.fields[field].queryset)
            self.assertNotIn('Autocomplete', type(form.fields[field].widget.widget).__name__)

    def test_client_link_select_does_not_require_user_admin_access(self):
        staff = User.objects.create_user(username='selector_staff', role='staff', is_staff=True)
        staff.user_permissions.add(*Permission.objects.filter(content_type__app_label='clients', codename__in=['add_client', 'change_client', 'view_client']))
        owner = User.objects.create_user(username='selector_client', role='client')
        self.client.force_login(staff)
        response = self.client.get('/admin/clients/client/add/')
        self.assertEqual(response.status_code, 200)
        form = response.context['adminform'].form
        self.assertIn(owner, form.fields['user'].queryset)
        self.assertNotIn('Autocomplete', type(form.fields['user'].widget.widget).__name__)
        self.assertEqual(self.client.get('/admin/accounts/user/').status_code, 403)
        saved = self.client.post('/admin/clients/client/add/', {'full_name': 'Sample link', 'status': 'active', 'user': owner.pk, '_save': 'Save'})
        self.assertEqual(saved.status_code, 302)
        self.assertTrue(Client.objects.filter(user=owner, created_by=staff).exists())
