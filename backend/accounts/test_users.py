"""User directory, admin account administration and password change APIs."""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from clients.models import Client

User = get_user_model()
PASSWORD = 'Directory-test-only-4821!'


class UserDirectoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username='dir_admin', role='admin', password=PASSWORD)
        cls.lawyer = User.objects.create_user(username='dir_lawyer', role='lawyer', password=PASSWORD, first_name='Law')
        cls.staff = User.objects.create_user(username='dir_staff', role='staff', password=PASSWORD)
        cls.client_user = User.objects.create_user(username='dir_client', role='client', password=PASSWORD)
        cls.unlinked = User.objects.create_user(username='dir_unlinked', role='client', password=PASSWORD)
        cls.inactive = User.objects.create_user(username='dir_inactive', role='lawyer', password=PASSWORD, is_active=False)
        Client.objects.create(user=cls.client_user, full_name='Linked', created_by=cls.admin)

    def setUp(self):
        cache.clear()
        self.api = APIClient()

    def as_user(self, user):
        self.api.force_authenticate(user)

    def test_firm_members_list_active_users_with_role_filter(self):
        for user in (self.lawyer, self.staff):
            self.as_user(user)
            response = self.api.get('/api/users/?role=lawyer')
            self.assertEqual(response.status_code, 200)
            names = {item['username'] for item in response.data['results']}
            self.assertEqual(names, {'dir_lawyer'})
            self.assertNotIn('email', response.data['results'][0])

    def test_admin_sees_inactive_and_contact_fields(self):
        self.as_user(self.admin)
        response = self.api.get('/api/users/?role=lawyer')
        self.assertEqual({item['username'] for item in response.data['results']}, {'dir_lawyer', 'dir_inactive'})
        self.assertIn('email', response.data['results'][0])
        self.assertNotIn('password', response.data['results'][0])

    def test_without_client_filter_lists_unlinked_logins(self):
        self.as_user(self.staff)
        response = self.api.get('/api/users/?without_client=1')
        self.assertEqual([item['username'] for item in response.data['results']], ['dir_unlinked'])

    def test_clients_and_anonymous_are_denied(self):
        self.assertEqual(self.api.get('/api/users/').status_code, 401)
        self.as_user(self.client_user)
        self.assertEqual(self.api.get('/api/users/').status_code, 403)

    def test_only_admin_creates_accounts_with_validated_password(self):
        payload = {'username': 'new_lawyer', 'first_name': 'New', 'role': 'lawyer', 'password': 'Strong-pass-9931!'}
        self.as_user(self.staff)
        self.assertEqual(self.api.post('/api/users/', payload, format='json').status_code, 403)
        self.as_user(self.admin)
        self.assertEqual(self.api.post('/api/users/', {**payload, 'password': '12345678'}, format='json').status_code, 400)
        response = self.api.post('/api/users/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn('password', response.data)
        self.api.force_authenticate(None)
        token = self.api.post('/api/auth/token/', {'username': 'new_lawyer', 'password': payload['password']}, format='json')
        self.assertEqual(token.status_code, 200)

    def test_admin_cannot_deactivate_self_and_can_deactivate_others(self):
        self.as_user(self.admin)
        self.assertEqual(self.api.patch(f'/api/users/{self.admin.pk}/', {'is_active': False}, format='json').status_code, 400)
        response = self.api.patch(f'/api/users/{self.staff.pk}/', {'is_active': False}, format='json')
        self.assertEqual(response.status_code, 200)
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)

    def test_change_password_requires_current_password(self):
        self.as_user(self.client_user)
        bad = self.api.post('/api/auth/change-password/', {'current_password': 'wrong', 'new_password': 'Another-pass-5521!'}, format='json')
        self.assertEqual(bad.status_code, 400)
        ok = self.api.post('/api/auth/change-password/', {'current_password': PASSWORD, 'new_password': 'Another-pass-5521!'}, format='json')
        self.assertEqual(ok.status_code, 200)
        self.client_user.refresh_from_db()
        self.assertTrue(self.client_user.check_password('Another-pass-5521!'))


class ListFilterTests(TestCase):
    """Dashboard filters added for the frontend."""
    @classmethod
    def setUpTestData(cls):
        from datetime import timedelta
        from django.utils import timezone
        from cases.models import Case
        from firm.models import PracticeArea
        from intake.models import Appointment, ConsultationRequest
        from billing.models import Invoice
        cls.admin = User.objects.create_user(username='flt_admin', role='admin', password=PASSWORD)
        cls.lawyer = User.objects.create_user(username='flt_lawyer', role='lawyer', password=PASSWORD)
        area = PracticeArea.objects.create(name='Area', slug='flt-area')
        c1 = Client.objects.create(full_name='One', created_by=cls.admin)
        c2 = Client.objects.create(full_name='Two', created_by=cls.admin)
        cls.case1 = Case.objects.create(case_number='F-1', title='A', client=c1, practice_area=area, created_by=cls.admin)
        case2 = Case.objects.create(case_number='F-2', title='B', client=c2, practice_area=area, created_by=cls.admin)
        start = timezone.now() + timedelta(days=3)
        Appointment.objects.create(client=c1, case=cls.case1, lawyer=cls.lawyer, start=start, end=start + timedelta(hours=1), created_by=cls.admin)
        Appointment.objects.create(client=c2, case=case2, lawyer=cls.lawyer, start=start + timedelta(hours=2), end=start + timedelta(hours=3), created_by=cls.admin)
        today = timezone.localdate()
        Invoice.objects.create(invoice_number='I-1', client=c1, case=cls.case1, issue_date=today, due_date=today, amount='10.00', created_by=cls.admin)
        Invoice.objects.create(invoice_number='I-2', client=c2, case=case2, issue_date=today, due_date=today, amount='10.00', created_by=cls.admin)
        ConsultationRequest.objects.create(name='N', phone='1', practice_area=area, message='m')

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.admin)

    def test_case_filters_for_appointments_and_invoices(self):
        self.assertEqual(self.api.get(f'/api/appointments/?case={self.case1.pk}').data['count'], 1)
        self.assertEqual(self.api.get(f'/api/invoices/?case={self.case1.pk}').data['count'], 1)
        self.assertEqual(self.api.get('/api/appointments/?status=bogus').status_code, 400)

    def test_status_filters_for_consultations_and_legal_aid(self):
        self.assertEqual(self.api.get('/api/consultations/?status=new').data['count'], 1)
        self.assertEqual(self.api.get('/api/consultations/?status=closed').data['count'], 0)
        self.assertEqual(self.api.get('/api/legal-aid/applications/?status=submitted').status_code, 200)
        self.assertEqual(self.api.get('/api/legal-aid/applications/?status=nope').status_code, 400)


class ClientAssignedLawyerTests(TestCase):
    """ERD: USER (lawyer) manages CLIENT via assigned_lawyer."""
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username='cal_admin', role='admin', password=PASSWORD)
        cls.lawyer = User.objects.create_user(username='cal_lawyer', role='lawyer', password=PASSWORD, first_name='Lead')
        cls.staff = User.objects.create_user(username='cal_staff', role='staff', password=PASSWORD)
        cls.portal = User.objects.create_user(username='cal_client', role='client', password=PASSWORD)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.staff)

    def test_assign_filter_and_client_sees_lawyer_name_only(self):
        r = self.api.post('/api/clients/', {'full_name': 'A', 'assigned_lawyer': self.lawyer.pk, 'user': self.portal.pk}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['assigned_lawyer_name'], 'Lead')
        self.api.post('/api/clients/', {'full_name': 'B'}, format='json')
        self.assertEqual(self.api.get(f'/api/clients/?assigned_lawyer={self.lawyer.pk}').data['count'], 1)
        self.assertEqual(self.api.get('/api/clients/?search=B').data['count'], 1)
        self.api.force_authenticate(self.portal)
        own = self.api.get('/api/clients/').data['results'][0]
        self.assertEqual(own['assigned_lawyer_name'], 'Lead')
        self.assertNotIn('assigned_lawyer', own)

    def test_non_lawyer_or_inactive_lawyer_rejected(self):
        r = self.api.post('/api/clients/', {'full_name': 'C', 'assigned_lawyer': self.staff.pk}, format='json')
        self.assertEqual(r.status_code, 400)
        self.lawyer.is_active = False
        self.lawyer.save()
        r = self.api.post('/api/clients/', {'full_name': 'D', 'assigned_lawyer': self.lawyer.pk}, format='json')
        self.assertEqual(r.status_code, 400)
