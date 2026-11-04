from io import StringIO

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .admin import FirmProfileAdmin
from .models import FirmProfile, LawyerProfile, PracticeArea

User = get_user_model()


class PublicFirmAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.firm = FirmProfile.objects.create(
            name='Anadi Law Firm', name_bn='অনাদি ল ফার্ম',
            tagline='English fallback', about='Sample about', about_bn='নমুনা পরিচিতি',
        )
        cls.area = PracticeArea.objects.create(
            name='Family Law', name_bn='পারিবারিক আইন', slug='family-law',
            description='Sample description', description_bn='নমুনা বিবরণ', display_order=2,
        )
        cls.first_area = PracticeArea.objects.create(name='Civil Law', slug='civil-law', display_order=1)
        cls.hidden_area = PracticeArea.objects.create(name='Hidden Area', slug='hidden', is_active=False)
        cls.user = User.objects.create_user(
            username='private_username', first_name='Demo', last_name='Lawyer',
            email='private@example.test', phone='private-phone', role='lawyer',
        )
        cls.lawyer = LawyerProfile.objects.create(
            user=cls.user, full_name_bn='নমুনা আইনজীবী', title='Sample Advocate',
            title_bn='নমুনা আইনজীবী', bio='English bio', languages_bn='ইংরেজি, বাংলা',
            is_public=True,
        )
        cls.lawyer.practice_areas.set([cls.area, cls.hidden_area])
        hidden_user = User.objects.create_user(username='hidden_lawyer', role='lawyer')
        cls.hidden_lawyer = LawyerProfile.objects.create(user=hidden_user, title='Hidden', is_public=False)

    def setUp(self):
        self.client = APIClient()

    def public_urls(self):
        return [
            reverse('firm:profile'),
            reverse('firm:practice-area-list'),
            reverse('firm:practice-area-detail', args=[self.area.slug]),
            reverse('firm:lawyer-list'),
            reverse('firm:lawyer-detail', args=[self.lawyer.pk]),
        ]

    def test_all_five_endpoints_allow_anonymous_read(self):
        for url in self.public_urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_all_public_endpoints_reject_write_methods(self):
        for url in self.public_urls():
            for method in ['post', 'put', 'patch', 'delete']:
                with self.subTest(url=url, method=method):
                    self.assertEqual(getattr(self.client, method)(url, {}, format='json').status_code, 405)

    def test_staff_also_cannot_write_through_public_api(self):
        staff = User.objects.create_user(username='admin_api', role='admin', is_staff=True)
        self.client.force_authenticate(staff)
        for url in self.public_urls():
            self.assertEqual(self.client.patch(url, {'name': 'Changed'}, format='json').status_code, 405)
        self.firm.refresh_from_db()
        self.assertEqual(self.firm.name, 'Anadi Law Firm')

    def test_practice_areas_are_filtered_and_ordered(self):
        response = self.client.get(reverse('firm:practice-area-list'))
        self.assertEqual(response.data['count'], 2)
        self.assertEqual([item['slug'] for item in response.data['results']], ['civil-law', 'family-law'])

    def test_inactive_area_cannot_be_retrieved_directly(self):
        self.assertEqual(self.client.get(reverse('firm:practice-area-detail', args=['hidden'])).status_code, 404)

    def test_hidden_lawyer_cannot_be_listed_or_retrieved(self):
        response = self.client.get(reverse('firm:lawyer-list'))
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(self.client.get(reverse('firm:lawyer-detail', args=[self.hidden_lawyer.pk])).status_code, 404)

    def test_inactive_user_hides_public_lawyer_profile(self):
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        self.assertEqual(self.client.get(reverse('firm:lawyer-list')).data['count'], 0)
        self.assertEqual(self.client.get(reverse('firm:lawyer-detail', args=[self.lawyer.pk])).status_code, 404)

    def test_changed_user_role_hides_public_lawyer_profile(self):
        self.user.role = 'client'
        self.user.save(update_fields=['role'])
        self.assertEqual(self.client.get(reverse('firm:lawyer-list')).data['count'], 0)
        self.assertEqual(self.client.get(reverse('firm:lawyer-detail', args=[self.lawyer.pk])).status_code, 404)

    def test_lawyer_response_excludes_private_user_fields_and_inactive_areas(self):
        data = self.client.get(reverse('firm:lawyer-detail', args=[self.lawyer.pk])).data
        self.assertEqual(set(data), {
            'id', 'full_name', 'photo', 'title', 'bio',
            'practice_areas', 'experience_years', 'languages',
        })
        self.assertEqual(data['full_name'], 'Demo Lawyer')
        self.assertEqual([area['slug'] for area in data['practice_areas']], ['family-law'])
        for value in ['private_username', 'private@example.test', 'private-phone']:
            self.assertNotIn(value, str(data))

    def test_bangla_content_and_per_field_english_fallback(self):
        response = self.client.get(reverse('firm:profile'), HTTP_ACCEPT_LANGUAGE='bn')
        self.assertEqual(response.headers['Content-Language'], 'bn')
        self.assertEqual(response.data['name'], 'অনাদি ল ফার্ম')
        self.assertEqual(response.data['tagline'], 'English fallback')
        self.assertEqual(response.data['about'], 'নমুনা পরিচিতি')
        lawyer = self.client.get(reverse('firm:lawyer-detail', args=[self.lawyer.pk]), HTTP_ACCEPT_LANGUAGE='bn').data
        self.assertEqual(lawyer['full_name'], 'নমুনা আইনজীবী')
        self.assertEqual(lawyer['bio'], 'English bio')
        self.assertEqual(lawyer['practice_areas'][0]['name'], 'পারিবারিক আইন')
        self.assertEqual(lawyer['languages'], 'ইংরেজি, বাংলা')

    def test_english_is_default_and_unsupported_language_falls_back(self):
        for headers in [{}, {'HTTP_ACCEPT_LANGUAGE': 'fr'}]:
            response = self.client.get(reverse('firm:profile'), **headers)
            self.assertEqual(response.data['name'], 'Anadi Law Firm')
            self.assertEqual(response.headers['Content-Language'], 'en')

    def test_logo_uses_supplied_brand_asset_when_no_upload_exists(self):
        data = self.client.get(reverse('firm:profile')).data
        self.assertEqual(data['logo'], 'http://testserver/static/firm/anadi-law-firm.png')

    def test_uploaded_logo_url(self):
        self.firm.logo = 'firm/logos/approved.png'
        self.firm.save(update_fields=['logo'])
        self.assertEqual(self.client.get(reverse('firm:profile')).data['logo'],
                         'http://testserver/media/firm/logos/approved.png')

    def test_pagination_uses_twenty_items(self):
        PracticeArea.objects.bulk_create([
            PracticeArea(name=f'Area {i}', slug=f'area-{i}') for i in range(22)
        ])
        data = self.client.get(reverse('firm:practice-area-list')).data
        self.assertEqual(data['count'], 24)
        self.assertEqual(len(data['results']), 20)
        self.assertIsNotNone(data['next'])
        self.assertEqual(len(self.client.get(reverse('firm:practice-area-list') + '?page=2').data['results']), 4)

    def test_missing_resources_return_404(self):
        for url in ['/api/practice-areas/missing/', '/api/lawyers/999999/']:
            self.assertEqual(self.client.get(url).status_code, 404)
        self.firm.delete()
        self.assertEqual(self.client.get(reverse('firm:profile')).status_code, 404)

    def test_private_file_urls_are_not_exposed(self):
        self.assertEqual(self.client.get('/private_media/secret.pdf').status_code, 404)


class FirmModelTests(TestCase):
    def test_single_firm_is_database_enforced(self):
        FirmProfile.objects.create(name='Anadi')
        with self.assertRaises(IntegrityError), transaction.atomic():
            FirmProfile.objects.create(pk=2, name='Second firm')

    def test_admin_disables_second_profile_creation(self):
        user = User.objects.create_superuser(username='admin', password='test-only-password')
        request = RequestFactory().get('/admin/firm/firmprofile/add/')
        request.user = user
        model_admin = FirmProfileAdmin(FirmProfile, admin.site)
        self.assertTrue(model_admin.has_add_permission(request))
        FirmProfile.objects.create(name='Anadi')
        self.assertFalse(model_admin.has_add_permission(request))

    def test_non_lawyer_cannot_be_selected_for_profile(self):
        user = User.objects.create_user(username='client', role='client')
        with self.assertRaises(ValidationError):
            LawyerProfile(user=user, title='Wrong role').full_clean()

    def test_profiles_default_to_private(self):
        user = User.objects.create_user(username='lawyer', role='lawyer')
        profile = LawyerProfile.objects.create(user=user, title='Advocate')
        self.assertFalse(profile.is_public)

    def test_duplicate_practice_slug_is_rejected(self):
        PracticeArea.objects.create(name='One', slug='same')
        with self.assertRaises(IntegrityError), transaction.atomic():
            PracticeArea.objects.create(name='Two', slug='same')

    def test_timestamps_are_populated(self):
        area = PracticeArea.objects.create(name='One', slug='one')
        self.assertIsNotNone(area.created_at)
        self.assertIsNotNone(area.updated_at)

    def test_brand_image_limits(self):
        for name, data in [('bad.svg', b'<svg/>'), ('huge.png', b'x' * (5 * 1024 * 1024 + 1))]:
            with self.subTest(name=name):
                firm = FirmProfile(name='Test', logo=SimpleUploadedFile(name, data))
                with self.assertRaises(ValidationError):
                    firm.full_clean()


class SeedFirmTests(TestCase):
    def seed(self):
        call_command('seed_firm', stdout=StringIO())

    def test_seed_is_repeatable_and_creates_expected_demo_content(self):
        self.seed()
        self.seed()
        self.assertEqual(FirmProfile.objects.count(), 1)
        self.assertEqual(PracticeArea.objects.count(), 5)
        self.assertEqual(LawyerProfile.objects.count(), 3)
        for user in User.objects.filter(username__startswith='stage2_demo_lawyer_'):
            self.assertFalse(user.has_usable_password())
            self.assertEqual(user.role, 'lawyer')
        self.assertEqual(APIClient().get('/api/lawyers/').data['count'], 3)

    def test_seed_preserves_edited_content(self):
        self.seed()
        firm = FirmProfile.objects.get()
        firm.name = 'Approved name'
        firm.save()
        area = PracticeArea.objects.get(slug='family-law')
        area.is_active = False
        area.save()
        self.seed()
        firm.refresh_from_db()
        area.refresh_from_db()
        self.assertEqual(firm.name, 'Approved name')
        self.assertFalse(area.is_active)

    def test_conflicting_seed_user_rolls_back_all_seed_content(self):
        User.objects.create_user(username='stage2_demo_lawyer_1', role='client')
        with self.assertRaises(CommandError):
            self.seed()
        self.assertEqual(FirmProfile.objects.count(), 0)
        self.assertEqual(PracticeArea.objects.count(), 0)
        self.assertEqual(LawyerProfile.objects.count(), 0)
