from uuid import uuid4
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from accounts.permissions import is_firm_member
from clients.models import Client
from cases.models import Case
from .models import LegalAidApplication


@transaction.atomic
def convert_application(pk, actor):
    if not is_firm_member(actor):
        raise PermissionDenied
    application = LegalAidApplication.objects.select_for_update().get(pk=pk)
    if application.status == 'matched':
        return application, False
    if application.status == 'declined':
        raise ValidationError('Reopen the application for review before conversion.')
    client = Client.objects.create(full_name=application.applicant_name, phone=application.phone, email=application.email, notes=application.description, created_by=actor)
    case = Case.objects.create(case_number='LA-' + uuid4().hex, title='Legal aid matter', client=client, practice_area=application.practice_area, created_by=actor)
    application.client, application.case, application.status, application.reviewed_by = client, case, 'matched', actor
    application.save()
    return application, True
