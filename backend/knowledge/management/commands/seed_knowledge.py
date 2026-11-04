from django.core.management.base import BaseCommand
from knowledge.models import Jurisdiction, RightsTopic, KnowledgeArticle, FAQ


class Command(BaseCommand):
    help = 'Create labelled English/Bangla sample drafts without asserting legal review.'
    def handle(self, *args, **options):
        bd, _ = Jurisdiction.objects.get_or_create(code='bd', defaults={'name': 'Bangladesh', 'name_bn': 'বাংলাদেশ', 'is_active': True, 'flag': '🇧🇩'})
        Jurisdiction.objects.get_or_create(code='gb', defaults={'name': 'United Kingdom', 'is_active': False})
        topic, _ = RightsTopic.objects.get_or_create(slug='sample-getting-help', defaults={'title': 'Sample: getting help', 'title_bn': 'নমুনা: সহায়তা'})
        for language, title, body in [('en', 'Sample: consultation information', 'Demonstration placeholder. Ask the firm about consultation arrangements. No legal procedure is described here.'), ('bn', 'নমুনা: পরামর্শের তথ্য', 'এটি প্রদর্শনের নমুনা। পরামর্শের ব্যবস্থা জানতে প্রতিষ্ঠানের সাথে যোগাযোগ করুন। এটি আইনি নির্দেশনা নয়।')]:
            KnowledgeArticle.objects.get_or_create(slug=f'sample-help-{language}', defaults=dict(jurisdiction=bd, topic=topic, title=title, summary=body, body=body, source_reference='Demo placeholder; replace with a verified source before real use.', language=language, is_sample=True))
            FAQ.objects.get_or_create(topic=topic, jurisdiction=bd, language=language, question=title, defaults={'answer': body, 'is_sample': True})
        self.stdout.write('Sample drafts created. An authorized reviewer must review and publish them in Admin.')
