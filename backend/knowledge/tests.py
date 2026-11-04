from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient
from .models import Jurisdiction, RightsTopic, KnowledgeArticle, FAQ
from .services import review_content


class KnowledgeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.reviewer = get_user_model().objects.create_superuser(username='reviewer', password='test-review-only')
        cls.bd = Jurisdiction.objects.create(name='Bangladesh', name_bn='বাংলাদেশ', code='bd', is_active=True)
        cls.topic = RightsTopic.objects.create(title='Sample', slug='sample')

    def setUp(self):
        self.api = APIClient()
        self.article = KnowledgeArticle.objects.create(jurisdiction=self.bd, topic=self.topic, title='Sample help', slug='sample-help', summary='Sample help', body='Not legal advice', source_reference='Demo', is_sample=True)
        self.faq = FAQ.objects.create(jurisdiction=self.bd, topic=self.topic, question='Sample help?', answer='Demonstration only', is_sample=True)

    def publish(self, obj):
        review_content(type(obj), obj.pk, self.reviewer)
        return review_content(type(obj), obj.pk, self.reviewer, publish=True)

    def test_draft_and_reviewed_not_public(self):
        for status in ('draft', 'reviewed'):
            if status == 'reviewed':
                review_content(KnowledgeArticle, self.article.pk, self.reviewer)
            self.assertEqual(self.api.get('/api/articles/').data['count'], 0)
            self.assertEqual(self.api.get('/api/articles/sample-help/').status_code, 404)
            self.assertEqual(self.api.get('/api/knowledge/search/?q=Sample').data['count'], 0)

    def test_public_published_disclaimer_and_search(self):
        self.publish(self.article)
        self.publish(self.faq)
        result = self.api.get('/api/knowledge/search/?q=Sample')
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data['count'], 2)
        self.assertEqual({r['type'] for r in result.data['results']}, {'article', 'faq'})
        for item in result.data['results']:
            self.assertIn('disclaimer', item)
            self.assertNotIn('reviewed_by', item)

    def test_edit_requires_new_review(self):
        obj = self.publish(self.article)
        obj.body = 'Changed body'
        obj.save()
        self.assertEqual(obj.status, 'draft')
        self.assertIsNone(obj.reviewed_at)
        self.assertEqual(self.api.get('/api/articles/').data['count'], 0)

    def test_inactive_country_and_topic_hidden(self):
        self.publish(self.article)
        self.bd.is_active = False
        self.bd.save()
        self.assertEqual(self.api.get('/api/articles/').data['count'], 0)
        self.assertEqual(self.api.get('/api/jurisdictions/').data['count'], 1)
        self.bd.is_active = True
        self.bd.save()
        self.topic.is_active = False
        self.topic.save()
        self.assertEqual(self.api.get('/api/knowledge/search/?q=Sample').data['count'], 0)

    def test_publish_without_review_rejected(self):
        with self.assertRaises(ValidationError):
            review_content(KnowledgeArticle, self.article.pk, self.reviewer, publish=True)
        self.article.status = 'published'
        with self.assertRaises(ValidationError):
            self.article.save()

    def test_staff_not_reviewer(self):
        staff = get_user_model().objects.create_user(username='staff', role='staff', is_superuser=True)
        with self.assertRaises(PermissionDenied):
            review_content(KnowledgeArticle, self.article.pk, staff)

    def test_filters_language_and_bangla_disclaimer(self):
        self.publish(self.article)
        self.assertEqual(self.api.get('/api/articles/?jurisdiction=gb').data['count'], 0)
        self.assertEqual(self.api.get('/api/articles/?language=bn').data['count'], 0)
        result = self.api.get('/api/articles/sample-help/', HTTP_ACCEPT_LANGUAGE='bn')
        self.assertIn('আইনি', result.data['disclaimer'])
        self.assertEqual(self.api.get('/api/jurisdictions/', HTTP_ACCEPT_LANGUAGE='bn').data['results'][0]['name'], 'বাংলাদেশ')

    def test_search_requires_bounded_query(self):
        self.assertEqual(self.api.get('/api/knowledge/search/').status_code, 400)
        self.assertEqual(self.api.get('/api/knowledge/search/', {'q': 'x' * 201}).status_code, 400)

    def test_public_cannot_write(self):
        self.assertEqual(self.api.post('/api/articles/', {}, format='json').status_code, 405)

    def test_seed_idempotent_and_not_published(self):
        call_command('seed_knowledge')
        count = KnowledgeArticle.objects.count()
        call_command('seed_knowledge')
        self.assertEqual(KnowledgeArticle.objects.count(), count)
        self.assertFalse(KnowledgeArticle.objects.filter(status='published').exists())

    def test_admin_review_and_publish_actions(self):
        self.client.force_login(self.reviewer)
        for action in ('mark_reviewed', 'publish'):
            response = self.client.post('/admin/knowledge/knowledgearticle/', {'action': action, '_selected_action': self.article.pk})
            self.assertEqual(response.status_code, 302)
        self.assertEqual(self.api.get('/api/articles/').data['count'], 1)
