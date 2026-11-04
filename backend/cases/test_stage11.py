from .tests import CaseFixtures


class CaseCompletionTests(CaseFixtures):
    def test_details_and_closed_date_validation(self):
        self.login(self.staff)
        url = f'/api/cases/{self.case.pk}/'
        payload = {'court': 'Sample court', 'opposite_party': 'Sample party', 'priority': 'high',
                   'filing_date': '2026-01-10', 'closed_date': '2026-01-11'}
        self.assertEqual(self.api.patch(url, payload, format='json').status_code, 400)
        payload['status'] = 'closed'
        payload['closed_date'] = '2026-01-09'
        self.assertEqual(self.api.patch(url, payload, format='json').status_code, 400)
        payload['closed_date'] = '2026-01-11'
        result = self.api.patch(url, payload, format='json')
        self.assertEqual(result.status_code, 200, result.data)
        self.login(self.owner)
        result = self.api.get(url)
        self.assertEqual(result.data['court'], 'Sample court')
        self.assertNotIn('opposite_party', result.data)
        self.assertNotIn('priority', result.data)

    def test_staff_assignment_and_duplicate_alias_validation(self):
        self.login(self.staff)
        payload = {'case': self.case.pk, 'user': self.staff.pk, 'role': 'support'}
        response = self.api.post('/api/case-assignments/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(response.data['lawyer'])
        self.assertEqual(self.api.post('/api/case-assignments/', payload, format='json').status_code, 400)
        for extra in ({'user': self.owner.pk}, {'user': self.admin_user.pk},
                      {'user': self.other_lawyer.pk, 'lawyer': self.other_lawyer.pk},
                      {'user': self.other_lawyer.pk, 'role': 'invalid'}):
            self.assertEqual(self.api.post('/api/case-assignments/', dict(payload, **extra), format='json').status_code, 400)

    def test_lead_lawyer_visible_and_legacy_filter_preserved(self):
        self.login(self.staff)
        response = self.api.post('/api/case-assignments/', {'case': self.case.pk, 'user': self.other_lawyer.pk, 'role': 'lead'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.login(self.owner)
        response = self.api.get(f'/api/cases/?lawyer={self.other_lawyer.pk}')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['lead_lawyers'][0]['id'], self.other_lawyer.pk)
