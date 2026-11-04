from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import close_old_connections, connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Pathway, Course, LiveSession, SessionRegistration


class AcademyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pathway = Pathway.objects.create(title='Sample', title_bn='নমুনা', slug='sample')
        cls.course = Course.objects.create(pathway=cls.pathway, title='Sample course', summary='Demo', duration='1 hour', instructor='Sample', is_published=True)
        cls.start = timezone.now() + timedelta(days=1)
        cls.session = LiveSession.objects.create(course=cls.course, title='Demo', start=cls.start, end=cls.start + timedelta(hours=1), venue='Demo', capacity=2, is_published=True)

    def setUp(self):
        self.api = APIClient()
        cache.clear()

    def register(self, email='sample@example.test', **kwargs):
        data = dict(session=self.session.pk, name='Sample Visitor', email=email)
        data.update(kwargs)
        return self.api.post('/api/session-registrations/', data, format='json')

    def test_public_lists_and_bangla(self):
        for path in ('pathways', 'courses', 'live-sessions'):
            response = self.api.get(f'/api/{path}/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['count'], 1)
        self.assertEqual(self.api.get('/api/pathways/', HTTP_ACCEPT_LANGUAGE='bn').data['results'][0]['title'], 'নমুনা')

    def test_inactive_pathway_hides_courses_and_sessions(self):
        self.pathway.is_active = False
        self.pathway.save()
        for path in ('pathways', 'courses', 'live-sessions'):
            self.assertEqual(self.api.get(f'/api/{path}/').data['count'], 0)
        self.assertEqual(self.register().status_code, 400)

    def test_draft_courses_and_sessions_not_public(self):
        self.course.is_published = False
        self.course.save()
        self.assertEqual(self.api.get(f'/api/courses/{self.course.pk}/').status_code, 404)
        self.assertEqual(self.api.get(f'/api/live-sessions/{self.session.pk}/').status_code, 404)
        self.assertEqual(self.register().status_code, 400)

    def test_registration_minimal_receipt_and_no_public_list(self):
        response = self.register()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(set(response.data), {'id', 'session', 'status'})
        self.assertEqual(self.api.get('/api/session-registrations/').status_code, 405)
        self.assertEqual(self.api.get('/api/live-sessions/').data['results'][0]['seats_remaining'], 1)

    def test_capacity_and_case_insensitive_duplicates(self):
        self.assertEqual(self.register().status_code, 201)
        self.assertEqual(self.register('SAMPLE@example.test').status_code, 400)
        self.assertEqual(self.register('second@example.test').status_code, 201)
        self.assertEqual(self.register('third@example.test').status_code, 400)
        self.assertEqual(SessionRegistration.objects.count(), 2)

    def test_user_link_cannot_be_forged(self):
        user = get_user_model().objects.create_user(username='learner', role='client')
        self.api.force_authenticate(user)
        response = self.register(user=999)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(SessionRegistration.objects.get().user_id, user.pk)

    def test_past_session_rejected(self):
        self.session.start = timezone.now() - timedelta(days=1)
        self.session.end = timezone.now() - timedelta(hours=1)
        self.session.save()
        self.assertEqual(self.register().status_code, 400)
        self.assertEqual(self.api.get('/api/live-sessions/').data['count'], 0)

    def test_session_validation_and_capacity_edit(self):
        self.register()
        self.register('second@example.test')
        self.session.capacity = 1
        with self.assertRaises(ValidationError):
            self.session.save()
        self.session.capacity = 2
        self.session.end = self.session.start
        with self.assertRaises(ValidationError):
            self.session.save()

    def test_honeypot_email_validation_and_throttle(self):
        self.assertEqual(self.register(website='bot').status_code, 400)
        self.assertEqual(self.register(email='bad').status_code, 400)
        for _ in range(3):
            self.register()
        self.assertEqual(self.register().status_code, 429)

    def test_seed_is_repeatable(self):
        call_command('seed_academy')
        count = LiveSession.objects.count()
        call_command('seed_academy')
        self.assertEqual(LiveSession.objects.count(), count)
        self.assertTrue(Course.objects.filter(is_sample=True).exists())

    def test_admin_forms_and_registration(self):
        admin = get_user_model().objects.create_superuser(username='admin', password='test-only')
        self.client.force_login(admin)
        for model in ('pathway', 'course', 'livesession', 'sessionregistration'):
            self.assertEqual(self.client.get(f'/admin/academy/{model}/add/').status_code, 200)
        response = self.client.post('/admin/academy/sessionregistration/add/', {'session': self.session.pk, 'name': 'Admin sample', 'email': 'admin-sample@example.test', '_save': 'Save'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SessionRegistration.objects.count(), 1)


@skipUnlessDBFeature('has_select_for_update')
class ConcurrentRegistrationTests(TransactionTestCase):
    def test_only_one_registration_gets_last_seat(self):
        start = timezone.now() + timedelta(days=1)
        session = LiveSession.objects.create(title='Concurrent sample', start=start, end=start + timedelta(hours=1), venue='Sample', capacity=1, is_published=True)
        barrier = Barrier(2)
        def worker(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                SessionRegistration.objects.create(session_id=session.pk, name='Sample', email=f'sample{index}@example.test')
                return True
            except ValidationError:
                return False
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, range(2)))
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(session.registrations.count(), 1)
