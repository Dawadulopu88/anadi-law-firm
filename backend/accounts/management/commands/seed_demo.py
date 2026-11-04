"""Create a repeatable, fictional local demonstration without shared passwords."""
from datetime import timedelta
from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction
from django.utils import timezone

from accounts.permissions import has_role
from academy.models import Course, LiveSession, SessionRegistration
from billing.models import Invoice, Payment
from cases.models import Case, CaseAssignment, CaseNote, Hearing, Task
from clients.models import Client
from documents.models import Document
from firm.models import PracticeArea
from intake.models import Appointment, ConsultationRequest
from legalaid.models import LegalAidApplication


class Command(BaseCommand):
    help = 'Seed a fictional local demo across all apps; preserve existing data and passwords.'

    def add_arguments(self, parser):
        parser.add_argument('--created-by', required=True, help='Existing active admin-role username.')

    def handle(self, *args, **options):
        if not settings.DEBUG and not getattr(settings, 'ALLOW_DEMO_SEED', False):
            raise CommandError('Demo seeding requires DEBUG=True locally or the explicit hosted demo profile.')
        actor = get_user_model().objects.filter(username=options['created_by']).first()
        if not has_role(actor, 'admin'):
            raise CommandError('--created-by must name an existing active admin-role user.')
        saved_files = []
        try:
            with transaction.atomic():
                # Serialize simultaneous runs of this command for the same actor.
                get_user_model().objects.select_for_update().get(pk=actor.pk)
                self.seed(actor, saved_files)
        except Exception:
            # Database rollback cannot remove a newly written storage object.
            for storage, name in saved_files:
                storage.delete(name)
            raise
        self.stdout.write(self.style.SUCCESS(
            'Demo ready: linked clients/cases, assignments, notes, hearing/task, appointment, '
            'private sample document, invoice/payment, legal aid and Academy registration. '
            'Knowledge remains draft; no verified helplines or shared passwords were created.'
        ))
        self.stdout.write('Portal username: stage3_demo_client_one. Set its password with manage.py changepassword.')
        self.stdout.write('Existing records, passwords and dates are preserved. Review future dates before a later demo.')

    def seed(self, actor, saved_files):
        for command in ('seed_firm', 'seed_stage3', 'seed_knowledge', 'seed_guided_help', 'seed_academy'):
            kwargs = {'created_by': actor.username} if command == 'seed_stage3' else {}
            call_command(command, stdout=StringIO(), **kwargs)
        User = get_user_model()
        owner = User.objects.get(username='stage3_demo_client_one')
        other = User.objects.get(username='stage3_demo_client_two')
        lawyer = User.objects.get(username='stage3_demo_lawyer')
        staff = User.objects.get(username='stage3_demo_staff')
        area = PracticeArea.objects.get(slug='family-law')
        client = Client.objects.get(user=owner)
        second_client = Client.objects.get(user=other)
        start = (timezone.now() + timedelta(days=7)).replace(hour=10, minute=0, second=0, microsecond=0)
        case, _ = Case.objects.get_or_create(case_number='DEMO-12-001', defaults={
            'title': 'Sample: meeting demonstration', 'description': 'Fictional sample only; no real legal matter.',
            'client': client, 'practice_area': area, 'court': 'Sample court', 'priority': 'normal', 'created_by': actor,
        })
        if case.client_id != client.pk:
            raise CommandError('DEMO-12-001 belongs to another client. No seed changes were saved.')
        Case.objects.get_or_create(case_number='DEMO-12-002', defaults={
            'title': 'Sample: second client privacy check', 'client': second_client, 'practice_area': area, 'created_by': actor,
        })
        CaseAssignment.objects.get_or_create(case=case, user=lawyer, defaults={'role': 'lead', 'assigned_by': actor})
        CaseAssignment.objects.get_or_create(case=case, user=staff, defaults={'role': 'support', 'assigned_by': actor})
        for internal, body in [(True, 'Sample internal strategy; not for the client.'), (False, 'Sample shared update for the client.')]:
            CaseNote.objects.get_or_create(case=case, body=body, defaults={'is_internal': internal, 'author': actor})
        Hearing.objects.get_or_create(case=case, court_name='Stage 12 sample court', defaults={
            'hearing_at': start, 'notes': 'Sample internal hearing note.'})
        Task.objects.get_or_create(case=case, title='Stage 12 sample: prepare documents', defaults={
            'due_date': start.date(), 'assigned_to': lawyer, 'created_by': actor})
        Appointment.objects.get_or_create(case=case, notes='Stage 12 sample appointment', defaults={
            'client': client, 'lawyer': lawyer, 'start': start + timedelta(hours=2),
            'end': start + timedelta(hours=3), 'created_by': actor})
        ConsultationRequest.objects.get_or_create(email='stage12-consultation@example.test', defaults={
            'name': 'Stage 12 sample visitor', 'phone': 'DEMO-NOT-A-PHONE', 'practice_area': area,
            'message': 'Fictional consultation request for an Admin conversion demo.', 'preferred_language': 'bn'})
        if not Document.objects.filter(case=case, title='Stage 12 private sample').exists():
            item = Document(case=case, title='Stage 12 private sample', document_type='sample', uploaded_by=actor)
            item.file = ContentFile(b'Fictional Anadi demonstration document. No real client information.', name='sample.txt')
            try:
                item.save()
            finally:
                if item.file._committed:
                    saved_files.append((item.file.storage, item.file.name))
        invoice, _ = Invoice.objects.get_or_create(invoice_number='DEMO-12-INV-001', defaults={
            'client': client, 'case': case, 'issue_date': timezone.localdate(), 'due_date': start.date(),
            'description': 'Fictional BDT demonstration invoice.', 'amount': '100.00', 'created_by': actor})
        if invoice.client_id != client.pk or invoice.case_id != case.pk:
            raise CommandError('DEMO-12-INV-001 has conflicting ownership. No seed changes were saved.')
        Payment.objects.get_or_create(invoice=invoice, reference='STAGE12-SAMPLE-40', defaults={
            'amount': '40.00', 'method': 'cash', 'date': timezone.localdate(), 'recorded_by': actor})
        LegalAidApplication.objects.get_or_create(email='stage12-aid@example.test', defaults={
            'applicant_name': 'Stage 12 sample applicant', 'phone': 'DEMO-NOT-A-PHONE', 'practice_area': area,
            'description': 'Fictional application; no eligibility decision has been made.',
            'income_range': 'Sample only', 'eligibility_answers': {'demo_only': True}})
        course = Course.objects.get(pathway__slug='sample-learning', title='Sample: finding support')
        session, _ = LiveSession.objects.get_or_create(course=course, title='Stage 12 sample meeting session', defaults={
            'title_bn': 'নমুনা: সভার জন্য সেশন', 'start': start + timedelta(days=1), 'end': start + timedelta(days=1, hours=1),
            'venue': 'Fictional demonstration only', 'capacity': 10, 'is_sample': True, 'is_published': True})
        SessionRegistration.objects.get_or_create(session=session, email='stage12-attendee@example.test', defaults={
            'name': 'Sample attendee', 'user': owner})
