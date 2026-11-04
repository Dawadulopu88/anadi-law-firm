from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from academy.models import Pathway, Course, LiveSession


class Command(BaseCommand):
    help = 'Create labelled bilingual Academy demo listings without real events.'
    @transaction.atomic
    def handle(self, *args, **kwargs):
        pathway, _ = Pathway.objects.get_or_create(slug='sample-learning', defaults={'title': 'Sample: learning pathway', 'title_bn': 'নমুনা: শেখার পথ', 'description': 'Demonstration only.', 'description_bn': 'শুধুমাত্র প্রদর্শনের জন্য।', 'is_sample': True})
        course, _ = Course.objects.get_or_create(pathway=pathway, title='Sample: finding support', defaults={'title_bn': 'নমুনা: সহায়তা খোঁজা', 'summary': 'Demo listing; no actual lesson or legal guidance.', 'summary_bn': 'নমুনা তালিকা; কোনো বাস্তব পাঠ বা আইনি নির্দেশনা নয়।', 'duration': '1 hour', 'duration_bn': '১ ঘণ্টা', 'instructor': 'Sample instructor', 'is_published': True, 'is_sample': True})
        start = (timezone.now() + timedelta(days=7)).replace(microsecond=0)
        LiveSession.objects.get_or_create(course=course, title='Sample: Academy demonstration', defaults={'title_bn': 'নমুনা: একাডেমি প্রদর্শন', 'start': start, 'end': start + timedelta(hours=1), 'venue': 'Demo only — no real event', 'venue_bn': 'শুধু নমুনা — বাস্তব অনুষ্ঠান নয়', 'capacity': 10, 'is_published': True, 'is_sample': True})
        self.stdout.write('Bilingual sample Academy listings created; no real event or registrations created.')
