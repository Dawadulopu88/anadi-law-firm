from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from clients.models import Client
from firm.models import PracticeArea
from intake.models import Appointment
from .models import Case, CaseAssignment, CaseNote

User = get_user_model()


class CaseFixtures(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser(username='admin', password='Test-only-case-481!')
        cls.staff = User.objects.create_user(username='staff', role='staff')
        cls.lawyer = User.objects.create_user(username='lawyer', role='lawyer', is_staff=True)
        cls.other_lawyer = User.objects.create_user(username='otherlawyer', role='lawyer')
        cls.owner = User.objects.create_user(username='owner', role='client')
        cls.outsider = User.objects.create_user(username='outsider', role='client')
        cls.one = Client.objects.create(full_name='Client One', user=cls.owner, created_by=cls.admin_user)
        cls.two = Client.objects.create(full_name='Client Two', user=cls.outsider, created_by=cls.admin_user)
        cls.area = PracticeArea.objects.create(name='Family', slug='family')
        cls.other_area = PracticeArea.objects.create(name='Civil', slug='civil')
        cls.case = Case.objects.create(case_number='AN-001', title='পারিবারিক মামলা', client=cls.one, practice_area=cls.area, created_by=cls.admin_user)
        cls.other_case = Case.objects.create(case_number='AN-002', title='Other case', client=cls.two, practice_area=cls.other_area, created_by=cls.admin_user)
        cls.assignment = CaseAssignment.objects.create(case=cls.case, user=cls.lawyer, assigned_by=cls.admin_user)
        cls.internal = CaseNote.objects.create(case=cls.case, body='Private legal strategy', author=cls.lawyer)
        cls.shared = CaseNote.objects.create(case=cls.case, body='Your case was filed', is_internal=False, author=cls.lawyer)
        cls.other_note = CaseNote.objects.create(case=cls.other_case, body='Other client update', is_internal=False, author=cls.admin_user)

    def setUp(self):
        self.api = APIClient()

    def login(self, user):
        self.api.force_authenticate(user)

    def payload(self, **changes):
        data = dict(case_number='AN-003', title='New case', client=self.one.pk, practice_area=self.area.pk)
        data.update(changes)
        return data

    def results(self, url):
        response = self.api.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data['results']


class CaseAPITests(CaseFixtures):
    def test_anonymous_endpoints_require_login(self):
        for path in ('cases', 'case-notes', 'case-assignments'):
            self.assertEqual(self.api.get(f'/api/{path}/').status_code, 401)
            self.assertEqual(self.api.post(f'/api/{path}/', {}, format='json').status_code, 401)

    def test_admin_and_staff_create_and_cannot_forge_creator(self):
        for user in (self.admin_user, self.staff):
            self.login(user)
            response = self.api.post('/api/cases/', self.payload(case_number=f'NEW-{user.pk}', created_by=self.owner.pk), format='json')
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(response.data['created_by'], user.pk)
            self.assertEqual(response.data['status'], 'open')

    def test_client_and_lawyer_cannot_create_cases(self):
        for user in (self.owner, self.lawyer):
            self.login(user)
            self.assertEqual(self.api.post('/api/cases/', self.payload(), format='json').status_code, 403)

    def test_client_list_detail_and_note_privacy(self):
        self.login(self.owner)
        cases = self.results('/api/cases/')
        self.assertEqual([item['id'] for item in cases], [self.case.pk])
        self.assertNotIn('created_by', cases[0])
        self.assertNotIn('client', cases[0])
        self.assertEqual(self.api.get(f'/api/cases/{self.other_case.pk}/').status_code, 404)
        notes = self.results('/api/case-notes/')
        self.assertEqual([note['id'] for note in notes], [self.shared.pk])
        self.assertNotIn('author', notes[0])
        self.assertNotIn('is_internal', notes[0])
        for note in (self.internal, self.other_note):
            self.assertEqual(self.api.get(f'/api/case-notes/{note.pk}/').status_code, 404)

    def test_client_cannot_mutate_any_case_or_note_or_read_assignments(self):
        self.login(self.owner)
        self.assertEqual(self.api.patch(f'/api/cases/{self.case.pk}/', {'status': 'closed'}, format='json').status_code, 403)
        self.assertEqual(self.api.post('/api/case-notes/', {'case': self.case.pk, 'body': 'forged'}, format='json').status_code, 403)
        self.assertEqual(self.api.get('/api/case-assignments/').status_code, 403)

    def test_lawyer_only_assigned_cases_and_notes(self):
        self.login(self.lawyer)
        self.assertEqual([c['id'] for c in self.results('/api/cases/')], [self.case.pk])
        self.assertEqual(len(self.results('/api/case-notes/')), 2)
        self.assertEqual(self.api.get(f'/api/cases/{self.other_case.pk}/').status_code, 404)
        self.assertEqual(self.api.patch(f'/api/cases/{self.other_case.pk}/', {'status': 'closed'}, format='json').status_code, 404)
        self.assertEqual(self.api.get(f'/api/case-notes/{self.other_note.pk}/').status_code, 404)
        self.assertEqual(self.api.post('/api/case-notes/', {'case': self.other_case.pk, 'body': 'Not allowed'}, format='json').status_code, 400)
        self.assertEqual(self.api.patch(f'/api/cases/{self.case.pk}/', {'status': 'in_progress'}, format='json').status_code, 200)

    def test_revocation_removes_lawyer_access_immediately(self):
        self.login(self.staff)
        self.assertEqual(self.api.delete(f'/api/case-assignments/{self.assignment.pk}/').status_code, 204)
        self.login(self.lawyer)
        self.assertEqual(self.results('/api/cases/'), [])
        self.assertEqual(self.results('/api/case-notes/'), [])
        self.assertEqual(self.api.get(f'/api/cases/{self.case.pk}/').status_code, 404)

    def test_staff_sees_all_cases_and_notes(self):
        self.login(self.staff)
        self.assertEqual(len(self.results('/api/cases/')), 2)
        self.assertEqual(len(self.results('/api/case-notes/')), 3)

    def test_unlinked_client_sees_empty_lists(self):
        self.login(User.objects.create_user(username='unlinked', role='client'))
        self.assertEqual(self.results('/api/cases/'), [])
        self.assertEqual(self.results('/api/case-notes/'), [])

    def test_role_superuser_does_not_bypass_ownership(self):
        self.owner.is_superuser = True
        self.owner.save()
        self.login(self.owner)
        self.assertEqual(self.api.get(f'/api/cases/{self.other_case.pk}/').status_code, 404)

    def test_inactive_user_rejected(self):
        self.staff.is_active = False
        self.staff.save()
        self.login(self.staff)
        self.assertEqual(self.api.get('/api/cases/').status_code, 403)

    def test_filter_search_order_and_pagination(self):
        self.login(self.staff)
        queries = ('status=open', f'practice_area={self.area.pk}', f'client={self.one.pk}', f'lawyer={self.lawyer.pk}', 'search=AN-001', 'search=পারিবারিক')
        for query in queries:
            data = self.results('/api/cases/?' + query)
            self.assertTrue(any(item['id'] == self.case.pk for item in data))
        self.assertEqual(len(self.results(f'/api/cases/?client={self.one.pk}&practice_area={self.other_area.pk}')), 0)
        response = self.api.get('/api/cases/?ordering=case_number')
        self.assertEqual(set(response.data), {'count', 'next', 'previous', 'results'})
        self.assertEqual([item['case_number'] for item in response.data['results']], ['AN-001', 'AN-002'])

    def test_filters_do_not_bypass_ownership(self):
        self.login(self.owner)
        for query in (f'client={self.two.pk}', 'search=AN-002', f'lawyer={self.other_lawyer.pk}'):
            self.assertEqual(self.results('/api/cases/?' + query), [])
        self.assertEqual(self.results(f'/api/case-notes/?case={self.other_case.pk}'), [])

    def test_malformed_filters_return_400(self):
        self.login(self.staff)
        for query in ('client=bad', 'practice_area=-1', 'lawyer=99999999999999999999999', 'status=invalid'):
            self.assertEqual(self.api.get('/api/cases/?' + query).status_code, 400)
        self.assertEqual(self.api.get('/api/case-notes/?case=bad').status_code, 400)

    def test_case_validation_duplicate_and_required_fields(self):
        self.login(self.staff)
        for data in ({}, self.payload(case_number='AN-001'), self.payload(status='invalid'), self.payload(filing_date='not-a-date'), self.payload(title='')):
            self.assertEqual(self.api.post('/api/cases/', data, format='json').status_code, 400)

    def test_client_cannot_be_reassigned_by_staff_or_lawyer(self):
        for user in (self.staff, self.lawyer):
            self.login(user)
            response = self.api.patch(f'/api/cases/{self.case.pk}/', {'client': self.two.pk}, format='json')
            self.assertEqual(response.status_code, 400)
        self.case.refresh_from_db()
        self.assertEqual(self.case.client_id, self.one.pk)

    def test_case_can_archive_but_not_delete(self):
        self.login(self.admin_user)
        self.assertEqual(self.api.patch(f'/api/cases/{self.case.pk}/', {'status': 'archived'}, format='json').status_code, 200)
        self.assertEqual(self.api.delete(f'/api/cases/{self.case.pk}/').status_code, 405)

    def test_inactive_client_and_practice_area_new_case_validation(self):
        self.login(self.staff)
        self.one.status = 'inactive'
        self.one.save()
        self.assertEqual(self.api.post('/api/cases/', self.payload(), format='json').status_code, 400)
        self.area.is_active = False
        self.area.save()
        self.assertEqual(self.api.post('/api/cases/', self.payload(client=self.two.pk), format='json').status_code, 400)
        self.assertEqual(self.api.patch(f'/api/cases/{self.case.pk}/', {'status': 'closed'}, format='json').status_code, 200)


class AssignmentAndNoteTests(CaseFixtures):
    def test_create_assignment_and_capture_actor(self):
        self.login(self.staff)
        data = {'case': self.case.pk, 'lawyer': self.other_lawyer.pk, 'assigned_by': self.owner.pk}
        response = self.api.post('/api/case-assignments/', data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['assigned_by'], self.staff.pk)
        self.login(self.other_lawyer)
        self.assertEqual(self.api.get(f'/api/cases/{self.case.pk}/').status_code, 200)

    def test_duplicate_and_invalid_assignments(self):
        self.login(self.staff)
        for lawyer in (self.lawyer, self.owner, self.staff):
            self.assertEqual(self.api.post('/api/case-assignments/', {'case': self.case.pk, 'lawyer': lawyer.pk}, format='json').status_code, 400)
        self.other_lawyer.is_active = False
        self.other_lawyer.save()
        self.assertEqual(self.api.post('/api/case-assignments/', {'case': self.case.pk, 'lawyer': self.other_lawyer.pk}, format='json').status_code, 400)

    def test_lawyer_cannot_self_assign_or_revoke(self):
        self.login(self.lawyer)
        self.assertEqual(self.api.post('/api/case-assignments/', {'case': self.other_case.pk, 'lawyer': self.lawyer.pk}, format='json').status_code, 403)
        self.assertEqual(self.api.delete(f'/api/case-assignments/{self.assignment.pk}/').status_code, 403)
        self.assertEqual(len(self.results('/api/case-assignments/')), 1)

    def test_assignments_cannot_be_edited(self):
        self.login(self.staff)
        self.assertEqual(self.api.patch(f'/api/case-assignments/{self.assignment.pk}/', {'case': self.other_case.pk}, format='json').status_code, 405)

    def test_note_internal_default_actor_and_shared_note(self):
        self.login(self.lawyer)
        response = self.api.post('/api/case-notes/', {'case': self.case.pk, 'body': 'অভ্যন্তরীণ আলোচনা', 'author': self.owner.pk}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data['is_internal'])
        self.assertEqual(response.data['author'], self.lawyer.pk)
        response = self.api.post('/api/case-notes/', {'case': self.case.pk, 'body': 'Shared update', 'is_internal': False}, format='json')
        self.assertEqual(response.status_code, 201)
        self.login(self.owner)
        self.assertEqual(len(self.results('/api/case-notes/')), 2)

    def test_notes_are_append_only(self):
        self.login(self.staff)
        self.assertEqual(self.api.patch(f'/api/case-notes/{self.internal.pk}/', {'is_internal': False}, format='json').status_code, 405)
        self.assertEqual(self.api.delete(f'/api/case-notes/{self.internal.pk}/').status_code, 405)
        self.internal.body = 'Changed'
        with self.assertRaises(ValidationError):
            self.internal.save()

    def test_note_empty_and_too_long_validation(self):
        self.login(self.staff)
        for body in ('', 'x' * 10001):
            self.assertEqual(self.api.post('/api/case-notes/', {'case': self.case.pk, 'body': body}, format='json').status_code, 400)

    def test_unique_assignment_database_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            CaseAssignment.objects.bulk_create([CaseAssignment(case=self.case, user=self.lawyer, assigned_by=self.staff)])


class AppointmentCaseTests(CaseFixtures):
    def appointment_payload(self, **changes):
        start = timezone.now() + timedelta(days=1)
        data = dict(client=self.one.pk, lawyer=self.lawyer.pk, start=start.isoformat(), end=(start + timedelta(hours=1)).isoformat())
        data.update(changes)
        return data

    def test_optional_case_and_matching_case(self):
        self.login(self.staff)
        response = self.api.post('/api/appointments/', self.appointment_payload(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(response.data['case'])
        path = f"/api/appointments/{response.data['id']}/"
        self.assertEqual(self.api.patch(path, {'case': self.case.pk}, format='json').status_code, 200)
        self.login(self.owner)
        self.assertEqual(self.api.get(path).data['case'], self.case.pk)

    def test_different_case_client_rejected_on_create_and_partial_update(self):
        self.login(self.staff)
        self.assertEqual(self.api.post('/api/appointments/', self.appointment_payload(case=self.other_case.pk), format='json').status_code, 400)
        response = self.api.post('/api/appointments/', self.appointment_payload(case=self.case.pk), format='json')
        self.assertEqual(response.status_code, 201)
        path = f"/api/appointments/{response.data['id']}/"
        for data in ({'client': self.two.pk}, {'case': self.other_case.pk}):
            self.assertEqual(self.api.patch(path, data, format='json').status_code, 400)
        self.assertEqual(self.api.patch(path, {'case': None, 'client': self.two.pk}, format='json').status_code, 200)

    def test_lawyer_cannot_link_unassigned_case(self):
        self.login(self.other_lawyer)
        self.assertEqual(self.api.post('/api/appointments/', self.appointment_payload(case=self.case.pk), format='json').status_code, 400)

    def test_model_validates_client_relationship(self):
        start = timezone.now()
        with self.assertRaises(ValidationError):
            Appointment.objects.create(client=self.one, case=self.other_case, lawyer=self.lawyer, start=start, end=start + timedelta(hours=1), created_by=self.staff)


class CaseAdminTests(CaseFixtures):
    def setUp(self):
        super().setUp()
        self.lawyer.user_permissions.add(*Permission.objects.filter(content_type__app_label='cases'))

    def test_admin_pages_render(self):
        self.client.force_login(self.admin_user)
        for model, pk in (('case', self.case.pk), ('caseassignment', self.assignment.pk), ('casenote', self.shared.pk)):
            for suffix in ('', 'add/', f'{pk}/change/'):
                response = self.client.get(f'/admin/cases/{model}/' + suffix)
                self.assertEqual(response.status_code, 200)

    def test_lawyer_admin_hides_unassigned_records(self):
        self.client.force_login(self.lawyer)
        response = self.client.get('/admin/cases/case/')
        self.assertContains(response, 'AN-001')
        self.assertNotContains(response, 'AN-002')
        self.assertEqual(self.client.get(f'/admin/cases/case/{self.other_case.pk}/change/').status_code, 302)
        self.assertEqual(self.client.get('/admin/cases/case/add/').status_code, 403)
        self.assertEqual(self.client.get('/admin/cases/caseassignment/add/').status_code, 403)

    def test_client_role_cannot_access_admin_even_with_django_permissions(self):
        self.owner.is_staff = True
        self.owner.is_superuser = True
        self.owner.save()
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get('/admin/cases/case/').status_code, 403)
        self.assertEqual(self.client.get('/admin/cases/casenote/').status_code, 403)

    def test_admin_note_case_choices_reject_unassigned_case(self):
        self.client.force_login(self.lawyer)
        response = self.client.post('/admin/cases/casenote/add/', {'case': self.other_case.pk, 'body': 'Forbidden', 'is_internal': 'on', '_save': 'Save'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('case', response.context['adminform'].form.errors)
        self.assertFalse(CaseNote.objects.filter(body='Forbidden').exists())

    def test_admin_creates_case_and_note_with_actor(self):
        self.client.force_login(self.admin_user)
        response = self.client.post('/admin/cases/case/add/', self.payload(case_number='ADMIN-1', status='open', priority='normal', _save='Save'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Case.objects.get(case_number='ADMIN-1').created_by, self.admin_user)
        response = self.client.post('/admin/cases/casenote/add/', {'case': self.case.pk, 'body': 'Admin note', 'is_internal': 'on', '_save': 'Save'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CaseNote.objects.get(body='Admin note').author, self.admin_user)

    def test_admin_cannot_change_or_delete_notes(self):
        self.client.force_login(self.admin_user)
        self.assertEqual(self.client.post(f'/admin/cases/casenote/{self.shared.pk}/change/', {'body': 'changed'}).status_code, 403)
        self.assertEqual(self.client.get(f'/admin/cases/casenote/{self.shared.pk}/delete/').status_code, 403)
