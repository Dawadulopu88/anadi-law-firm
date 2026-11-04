from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from firm.models import FirmProfile, LawyerProfile, PracticeArea


class Command(BaseCommand):
    help = 'Create bilingual, clearly labelled Stage 2 sample content. Preserve existing content.'

    @transaction.atomic
    def handle(self, *args, **options):
        FirmProfile.objects.get_or_create(pk=1, defaults={
            'name': 'Anadi Law Firm',
            'name_bn': 'অনাদি ল ফার্ম',
            'tagline': 'Sample website — demonstration only',
            'tagline_bn': 'নমুনা ওয়েবসাইট — শুধুমাত্র প্রদর্শনের জন্য',
            'about': 'Sample firm profile. Replace with firm-approved information before publication.',
            'about_bn': 'এটি প্রতিষ্ঠানের নমুনা পরিচিতি। প্রকাশের আগে অনুমোদিত তথ্য দিন।',
        })
        areas = []
        for order, (slug, name, name_bn, icon) in enumerate([
            ('family-law', 'Family Law', 'পারিবারিক আইন', 'bi-people'),
            ('criminal-law', 'Criminal Law', 'ফৌজদারি আইন', 'bi-shield-check'),
            ('civil-law', 'Civil Law', 'দেওয়ানি আইন', 'bi-bank'),
            ('property-law', 'Property Law', 'সম্পত্তি আইন', 'bi-house'),
            ('corporate-law', 'Corporate Law', 'কোম্পানি আইন', 'bi-briefcase'),
        ], start=1):
            area, _ = PracticeArea.objects.get_or_create(slug=slug, defaults={
                'name': name, 'name_bn': name_bn, 'icon': icon, 'display_order': order,
                'description': 'Sample practice-area listing for the demo. This is not legal advice.',
                'description_bn': 'প্রদর্শনের জন্য নমুনা সেবার তালিকা। এটি আইনি পরামর্শ নয়।',
            })
            areas.append(area)
        User = get_user_model()
        for index, bangla_number in [(1, '১'), (2, '২'), (3, '৩')]:
            username = f'stage2_demo_lawyer_{index}'
            user, created = User.objects.get_or_create(username=username, defaults={
                'first_name': 'Sample Lawyer', 'last_name': str(index), 'role': 'lawyer',
            })
            if created:
                user.set_unusable_password()
                user.save(update_fields=['password'])
            elif user.role != 'lawyer':
                raise CommandError(f'{username} is already used by a non-lawyer. No seed changes were applied.')
            profile, created = LawyerProfile.objects.get_or_create(user=user, defaults={
                'full_name_bn': f'নমুনা আইনজীবী {bangla_number}',
                'title': 'Sample advocate — demo only',
                'title_bn': 'নমুনা আইনজীবী — শুধুমাত্র প্রদর্শনের জন্য',
                'bio': 'Fictional demo profile. Replace with an approved real lawyer profile before publication.',
                'bio_bn': 'কাল্পনিক নমুনা পরিচিতি। প্রকাশের আগে অনুমোদিত আইনজীবীর পরিচিতি দিন।',
                'languages': 'English, Bangla', 'languages_bn': 'ইংরেজি, বাংলা',
                'is_public': True,
            })
            if created:
                profile.practice_areas.set(areas[index - 1:index + 1])
        self.stdout.write(self.style.SUCCESS(
            'Sample firm content is ready: 5 practice areas and 3 sample lawyer profiles. '
            'Existing content was preserved. Demo lawyer accounts cannot log in.'
        ))
