from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from accounts.permissions import is_firm_member
from clients.models import Client
from .models import ConsultationRequest


@transaction.atomic
def convert_consultation(request_id, actor):
    if not is_firm_member(actor):
        raise PermissionDenied('Only active firm members can convert consultation requests.')
    consultation = ConsultationRequest.objects.select_for_update().get(pk=request_id)
    if consultation.status == ConsultationRequest.Status.CONVERTED:
        return consultation, False
    if consultation.status == ConsultationRequest.Status.CLOSED:
        raise ValidationError({'status': 'Reopen a closed request as contacted before converting it.'})
    client = Client.objects.create(
        full_name=consultation.name, phone=consultation.phone, email=consultation.email,
        notes=f'Consultation request #{consultation.pk}:\n{consultation.message}',
        created_by=actor,
    )
    consultation.client = client
    consultation.status = ConsultationRequest.Status.CONVERTED
    consultation.handled_by = actor
    consultation.save()
    return consultation, True
