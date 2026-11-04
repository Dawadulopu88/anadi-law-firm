from django.core.management.base import BaseCommand
from django.db import transaction
from knowledge.models import GuidedFlow, GuidedQuestion, GuidedOption


class Command(BaseCommand):
    help = 'Create two labelled sample flows; never seed unverified helpline numbers.'
    @transaction.atomic
    def handle(self, *args, **options):
        for purpose, name, name_bn, question, question_bn, choices in [
            ('issue_finder', 'Sample: What kind of legal help do I need?', 'নমুনা: কী ধরনের আইনি সহায়তা চাই?', 'What would you like to discuss?', 'কোন বিষয়ে আলোচনা করতে চান?', [('Family or personal matter', 'পারিবারিক বা ব্যক্তিগত বিষয়'), ('Another matter', 'অন্য বিষয়')]),
            ('eligibility', 'Sample: Am I eligible for legal aid?', 'নমুনা: আমি কি আইনি সহায়তা পেতে পারি?', 'Would you like the firm to review your circumstances?', 'আপনার পরিস্থিতি পর্যালোচনার জন্য যোগাযোগ করতে চান?', [('Yes, request a review', 'হ্যাঁ, পর্যালোচনা চাই'), ('I need more information', 'আরও তথ্য চাই')]),
        ]:
            flow, created = GuidedFlow.objects.get_or_create(name=name, defaults={'name_bn': name_bn, 'purpose': purpose, 'is_sample': True})
            if not created:
                continue
            start = GuidedQuestion.objects.create(flow=flow, text=question, text_bn=question_bn)
            for label, label_bn in choices:
                GuidedOption.objects.create(question=start, label=label, label_bn=label_bn, escalate_to_consultation=True)
            flow.start_question, flow.is_active = start, True
            flow.save()
        self.stdout.write('Two sample indicative flows are available. No support phone numbers were seeded.')
