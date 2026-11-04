from datetime import timedelta
from django.utils import timezone
from .tests import CaseFixtures
from .models import Hearing, Task


class WorkTests(CaseFixtures):
    def setUp(self):
        super().setUp()
        self.hearing = Hearing.objects.create(case=self.case, court_name='Demo court', hearing_at=timezone.now() + timedelta(days=2), notes='Private preparation')
        self.task = Task.objects.create(case=self.case, title='Prepare', due_date=timezone.localdate(), assigned_to=self.lawyer, created_by=self.staff)

    def test_client_hearings_scoped_without_notes(self):
        self.login(self.owner)
        data = self.results('/api/hearings/upcoming/')
        self.assertEqual(len(data), 1)
        self.assertNotIn('notes', data[0])
        self.login(self.outsider)
        self.assertEqual(self.results('/api/hearings/'), [])
        self.assertEqual(self.api.get(f'/api/hearings/{self.hearing.pk}/').status_code, 404)

    def test_client_cannot_write_hearings_or_access_tasks(self):
        self.login(self.owner)
        self.assertEqual(self.api.post('/api/hearings/', {}, format='json').status_code, 403)
        self.assertEqual(self.api.get('/api/tasks/').status_code, 403)

    def test_lawyer_cannot_access_unassigned_work(self):
        self.login(self.other_lawyer)
        self.assertEqual(self.results('/api/hearings/'), [])
        self.assertEqual(self.results('/api/tasks/'), [])
        self.assertEqual(self.api.delete(f'/api/tasks/{self.task.pk}/').status_code, 404)

    def test_hearing_validation_and_crud(self):
        self.login(self.staff)
        path = f'/api/hearings/{self.hearing.pk}/'
        self.assertEqual(self.api.patch(path, {'next_hearing_date': (timezone.now() - timedelta(days=1)).isoformat()}, format='json').status_code, 400)
        self.assertEqual(self.api.patch(path, {'case': self.other_case.pk}, format='json').status_code, 400)
        self.assertEqual(self.api.patch(path, {'outcome': 'Adjourned'}, format='json').status_code, 200)
        self.assertEqual(self.api.delete(path).status_code, 204)

    def test_my_tasks_and_assignment_validation(self):
        self.login(self.lawyer)
        self.assertEqual(len(self.results('/api/tasks/my-tasks/')), 1)
        payload = {'case': self.case.pk, 'title': 'New', 'due_date': str(timezone.localdate()), 'assigned_to': self.other_lawyer.pk}
        self.assertEqual(self.api.post('/api/tasks/', payload, format='json').status_code, 400)
        payload.update(case=None, assigned_to=self.staff.pk)
        self.assertEqual(self.api.post('/api/tasks/', payload, format='json').status_code, 400)
        payload.update(assigned_to=self.lawyer.pk, created_by=self.staff.pk)
        response = self.api.post('/api/tasks/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['created_by'], self.lawyer.pk)

    def test_revoking_case_assignment_hides_tasks(self):
        self.assignment.delete()
        self.login(self.lawyer)
        self.assertEqual(self.results('/api/tasks/my-tasks/'), [])

    def test_admin_forms(self):
        self.client.force_login(self.admin_user)
        for model in ('hearing', 'task'):
            for suffix in ('', 'add/'):
                self.assertEqual(self.client.get(f'/admin/cases/{model}/{suffix}').status_code, 200)
