from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from cases.tests import CaseFixtures
from cases.models import Hearing
from intake.models import Appointment
from documents.models import Document
from billing.models import Invoice, Payment


class PortalTests(CaseFixtures):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        start = timezone.now() + timedelta(days=2)
        cls.hearing = Hearing.objects.create(case=cls.case, court_name='Sample', hearing_at=start, notes='Private hearing notes')
        Hearing.objects.create(case=cls.other_case, court_name='Other', hearing_at=start)
        Hearing.objects.create(case=cls.case, court_name='Past', hearing_at=start - timedelta(days=3))
        cls.appointment = Appointment.objects.create(client=cls.one, case=cls.case, lawyer=cls.lawyer, start=start, end=start + timedelta(hours=1), notes='Private appointment notes', created_by=cls.staff)
        Appointment.objects.create(client=cls.two, case=cls.other_case, lawyer=cls.other_lawyer, start=start, end=start + timedelta(hours=1), created_by=cls.staff)
        # Metadata fixtures only; download behavior uses real temporary files in documents.tests.
        cls.document = Document.objects.create(case=cls.case, title='Shared sample', document_type='fixture', file='fixtures/shared.txt', uploaded_by=cls.staff, is_client_visible=True)
        Document.objects.create(case=cls.case, title='Internal sample', document_type='fixture', file='fixtures/internal.txt', uploaded_by=cls.staff)
        Document.objects.create(case=cls.other_case, title='Other sample', document_type='fixture', file='fixtures/other.txt', uploaded_by=cls.staff, is_client_visible=True)
        cls.invoice = Invoice.objects.create(invoice_number='PORTAL-1', client=cls.one, case=cls.case, amount=Decimal('100.00'), issue_date=timezone.localdate(), due_date=timezone.localdate(), created_by=cls.staff)
        Payment.objects.create(invoice=cls.invoice, amount=Decimal('25.00'), method='cash', date=timezone.localdate(), recorded_by=cls.staff)
        Invoice.objects.create(invoice_number='OTHER-1', client=cls.two, amount=Decimal('999.00'), issue_date=timezone.localdate(), due_date=timezone.localdate(), created_by=cls.staff)

    def test_summary_is_client_specific(self):
        self.login(self.owner)
        response = self.api.get('/api/portal/summary/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, {'cases': 1, 'active_cases': 1, 'upcoming_hearings': 1, 'upcoming_appointments': 1, 'documents': 1, 'invoices': 1, 'outstanding_balance': '75.00', 'currency': 'BDT'})

    def test_all_portal_lists_exclude_other_clients_and_internal_fields(self):
        self.login(self.owner)
        expected = {'cases': self.case.pk, 'hearings': self.hearing.pk, 'appointments': self.appointment.pk, 'documents': self.document.pk, 'invoices': self.invoice.pk}
        for resource, pk in expected.items():
            data = self.results(f'/api/portal/{resource}/?client={self.two.pk}')
            self.assertEqual([item['id'] for item in data], [pk])
            for field in ('notes', 'uploaded_by', 'created_by', 'file'):
                self.assertNotIn(field, data[0])

    def test_portal_requires_client_role(self):
        for resource in ('summary', 'cases', 'hearings', 'appointments', 'documents', 'invoices'):
            self.api.force_authenticate(None)
            self.assertEqual(self.api.get(f'/api/portal/{resource}/').status_code, 401)
            for user in (self.staff, self.lawyer, self.admin_user):
                self.login(user)
                self.assertEqual(self.api.get(f'/api/portal/{resource}/').status_code, 403)

    def test_unlinked_client_has_empty_portal(self):
        self.login(get_user_model().objects.create_user(username='newportal', role='client'))
        data = self.api.get('/api/portal/summary/').data
        self.assertEqual(data['cases'], 0)
        self.assertEqual(data['outstanding_balance'], '0.00')
        self.assertEqual(self.results('/api/portal/documents/'), [])

    def test_unlinking_client_removes_portal_access_to_records(self):
        self.one.user = None
        self.one.save()
        self.login(self.owner)
        self.assertEqual(self.results('/api/portal/cases/'), [])
        self.assertEqual(self.api.get('/api/portal/summary/').data['invoices'], 0)

    def test_portal_is_read_only(self):
        self.login(self.owner)
        self.assertEqual(self.api.post('/api/portal/cases/', {}, format='json').status_code, 405)
