from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from .models import GuidedFlow, GuidedQuestion, GuidedOption, HelpContact
from .guided import validate_flow


class GuidedTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.flow = GuidedFlow.objects.create(name='Sample flow', purpose='issue_finder')
        self.q = GuidedQuestion.objects.create(flow=self.flow, text='Choose?', text_bn='বেছে নিন')
        self.option = GuidedOption.objects.create(question=self.q, label='Consult', label_bn='পরামর্শ', escalate_to_consultation=True)
        self.flow.start_question, self.flow.is_active = self.q, True
        self.flow.save()

    def test_walk_flow_start_to_result(self):
        start = self.api.get(f'/api/guided-flows/{self.flow.pk}/start/')
        self.assertEqual(start.status_code, 200)
        self.assertIn('disclaimer', start.data)
        self.assertEqual(start.data['question']['options'][0]['id'], self.option.pk)
        result = self.api.get(f'/api/guided-options/{self.option.pk}/result/')
        self.assertTrue(result.data['indicative_only'])
        self.assertEqual(result.data['consultation_url'], '/api/consultations/')

    def test_bangla_questions(self):
        response = self.api.get(f'/api/guided-questions/{self.q.pk}/', HTTP_ACCEPT_LANGUAGE='bn')
        self.assertEqual(response.data['text'], 'বেছে নিন')
        self.assertEqual(response.data['options'][0]['label'], 'পরামর্শ')

    def test_edit_deactivates_flow_until_validated_again(self):
        self.option.label = 'Changed'
        self.option.save()
        self.assertEqual(self.api.get('/api/guided-flows/').data['count'], 0)
        self.assertEqual(self.api.get(f'/api/guided-questions/{self.q.pk}/').status_code, 404)

    def test_no_outcome_rejected(self):
        with self.assertRaises(ValidationError):
            GuidedOption.objects.create(question=self.q, label='Dead end')

    def test_cycle_cannot_activate(self):
        self.option.escalate_to_consultation = False
        self.option.next_question = self.q
        self.option.save()
        self.flow.is_active = True
        with self.assertRaises(ValidationError):
            self.flow.save()

    def test_cross_flow_question_rejected(self):
        other = GuidedFlow.objects.create(name='Other', purpose='eligibility')
        question = GuidedQuestion.objects.create(flow=other, text='Other?')
        with self.assertRaises(ValidationError):
            GuidedOption.objects.create(question=self.q, label='Cross', next_question=question)

    def test_deleted_option_hides_broken_flow(self):
        self.option.delete()
        self.assertEqual(self.api.get('/api/guided-flows/').data['count'], 0)
        self.assertEqual(self.api.get(f'/api/guided-flows/{self.flow.pk}/start/').status_code, 404)

    def test_unreachable_question_not_public(self):
        hidden = GuidedQuestion.objects.create(flow=self.flow, text='Unreachable')
        self.flow.is_active = True
        self.flow.save()
        self.assertEqual(self.api.get(f'/api/guided-questions/{hidden.pk}/').status_code, 404)

    def test_seeds_all_reach_results_idempotently(self):
        call_command('seed_guided_help')
        count = GuidedFlow.objects.count()
        call_command('seed_guided_help')
        self.assertEqual(GuidedFlow.objects.count(), count)
        for flow in GuidedFlow.objects.filter(is_active=True):
            self.assertTrue(validate_flow(flow))
        self.assertEqual(HelpContact.objects.count(), 0)

    def test_contacts_hidden_until_admin_records_verification(self):
        contact = HelpContact.objects.create(label='Test fixture only', phone='TEST-NOT-A-NUMBER', hours='Test', verification_reference='Test supervisor reference')
        self.assertEqual(self.api.get('/api/help-contacts/').data['count'], 0)
        admin = get_user_model().objects.create_superuser(username='reviewer', password='test-only')
        self.client.force_login(admin)
        self.client.post('/admin/knowledge/helpcontact/', {'action': 'record_verification', '_selected_action': contact.pk})
        self.assertEqual(self.api.get('/api/help-contacts/').data['count'], 1)
        contact.refresh_from_db()
        contact.phone = 'CHANGED-TEST'
        contact.save()
        self.assertEqual(self.api.get('/api/help-contacts/').data['count'], 0)
