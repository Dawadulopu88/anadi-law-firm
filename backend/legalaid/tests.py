from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import close_old_connections, connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from rest_framework.test import APIClient
from cases.tests import CaseFixtures
from clients.models import Client
from cases.models import Case
from firm.models import PracticeArea
from .models import LegalAidApplication
from .services import convert_application


class LegalAidTests(CaseFixtures):
    def setUp(self):
        super().setUp()
        cache.clear()

    def apply(self, **kwargs):
        data = dict(applicant_name='Sample Applicant', phone='TEST-ONLY', practice_area=self.area.pk, description='Private test description', income_range='Private range', eligibility_answers={'sample': True})
        data.update(kwargs)
        return self.api.post('/api/legal-aid/apply/', data, format='json')

    def test_apply_receipt_and_tracking_only_status(self):
        response = self.apply(status='matched', reviewed_by=self.staff.pk)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(set(response.data), {'tracking_code', 'status'})
        self.assertGreaterEqual(len(response.data['tracking_code']), 40)
        tracking = self.api.get('/api/legal-aid/track/' + response.data['tracking_code'] + '/')
        self.assertEqual(tracking.data, {'status': 'submitted'})
        self.assertEqual(tracking['Cache-Control'], 'no-store')
        self.assertEqual(self.api.get('/api/legal-aid/track/not-valid/').status_code, 404)

    def test_public_validation_and_throttle(self):
        self.assertEqual(self.apply(website='spam').status_code, 400)
        self.assertEqual(self.apply(eligibility_answers=['not', 'mapping']).status_code, 400)
        self.assertEqual(self.apply(eligibility_answers={'nested': {'bad': True}}).status_code, 400)
        self.assertEqual(self.apply(applicant_name='').status_code, 400)
        self.apply()
        self.assertEqual(self.apply().status_code, 429)

    def test_private_review_permissions(self):
        self.apply()
        application = LegalAidApplication.objects.get()
        path = f'/api/legal-aid/applications/{application.pk}/'
        self.assertEqual(self.api.get(path).status_code, 401)
        self.login(self.owner)
        self.assertEqual(self.api.get(path).status_code, 403)
        self.login(self.staff)
        response = self.api.patch(path, {'status': 'under_review', 'reviewed_by': self.owner.pk}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['reviewed_by'], self.staff.pk)

    def test_conversion_is_idempotent_and_cannot_reopen(self):
        self.apply()
        application = LegalAidApplication.objects.get()
        self.login(self.staff)
        path = f'/api/legal-aid/applications/{application.pk}/'
        first = self.api.post(path + 'convert/', {}, format='json')
        self.assertEqual(first.status_code, 201, first.data)
        second = self.api.post(path + 'convert/', {}, format='json')
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data['case'], second.data['case'])
        self.assertEqual(Case.objects.get(pk=first.data['case']).client_id, first.data['client'])
        self.assertEqual(self.api.patch(path, {'status': 'submitted'}, format='json').status_code, 400)

    def test_failed_conversion_rolls_back_client(self):
        self.apply()
        application = LegalAidApplication.objects.get()
        count = Client.objects.count()
        with patch('legalaid.services.Case.objects.create', side_effect=ValidationError('Test failure')):
            with self.assertRaises(ValidationError):
                convert_application(application.pk, self.staff)
        self.assertEqual(Client.objects.count(), count)
        application.refresh_from_db()
        self.assertIsNone(application.client_id)

    def test_admin_action(self):
        self.apply()
        application = LegalAidApplication.objects.get()
        self.client.force_login(self.admin_user)
        response = self.client.post('/admin/legalaid/legalaidapplication/', {'action': 'convert_selected', '_selected_action': application.pk})
        self.assertEqual(response.status_code, 302)
        application.refresh_from_db()
        self.assertEqual(application.status, 'matched')


@skipUnlessDBFeature('has_select_for_update')
class ConcurrentConversionTests(TransactionTestCase):
    def test_concurrent_conversion_produces_one_client_and_case(self):
        user = get_user_model().objects.create_user(username='reviewer', role='staff')
        area = PracticeArea.objects.create(name='Sample', slug='sample')
        application = LegalAidApplication.objects.create(applicant_name='Sample', phone='TEST', practice_area=area, description='Sample')
        barrier = Barrier(2)
        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                result, created = convert_application(application.pk, user)
                return result.client_id, result.case_id, created
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: worker(), range(2)))
        self.assertEqual(results[0][:2], results[1][:2])
        self.assertEqual(sum(r[2] for r in results), 1)
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(Case.objects.count(), 1)
