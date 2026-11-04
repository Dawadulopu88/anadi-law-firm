import secrets
import json
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from cases.models import ValidatedModel


def tracking_code():
    return secrets.token_urlsafe(32)


def validate_answers(value):
    if not isinstance(value, dict) or len(value) > 20 or len(json.dumps(value, ensure_ascii=False)) > 5000:
        raise ValidationError('Eligibility answers must be an object with at most 20 short answers (5000 characters total).')
    for key, answer in value.items():
        if len(key) > 100 or not isinstance(answer, (str, bool, int, float, type(None))) or len(str(answer)) > 500:
            raise ValidationError('Use short scalar eligibility answers.')


class LegalAidApplication(ValidatedModel):
    tracking_code = models.CharField(max_length=64, unique=True, default=tracking_code, editable=False)
    applicant_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    practice_area = models.ForeignKey('firm.PracticeArea', on_delete=models.PROTECT)
    description = models.TextField(max_length=5000)
    income_range = models.CharField(max_length=100, blank=True)
    eligibility_answers = models.JSONField(default=dict, blank=True, validators=[validate_answers])
    status = models.CharField(max_length=12, choices=[('submitted', 'Submitted'), ('under_review', 'Under review'), ('matched', 'Matched'), ('declined', 'Declined')], default='submitted')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='reviewed_legal_aid')
    client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, null=True, blank=True, related_name='legal_aid_applications')
    case = models.ForeignKey('cases.Case', on_delete=models.PROTECT, null=True, blank=True, related_name='legal_aid_applications')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        constraints = [models.CheckConstraint(condition=(models.Q(status='matched', client__isnull=False, case__isnull=False) | (~models.Q(status='matched') & models.Q(client__isnull=True, case__isnull=True))), name='legalaid_consistent_conversion')]

    def clean(self):
        super().clean()
        if (self.status == 'matched') != bool(self.client_id and self.case_id) or bool(self.client_id) != bool(self.case_id):
            raise ValidationError({'status': 'Use conversion to match an application to a client and case.'})
        if self.case_id and self.case.client_id != self.client_id:
            raise ValidationError({'case': 'Client and case must match.'})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.pk:
                old = type(self).objects.select_for_update().get(pk=self.pk)
                if old.status == 'matched' and (self.status != 'matched' or self.client_id != old.client_id or self.case_id != old.case_id):
                    raise ValidationError('A converted application cannot be unlinked or reopened.')
            return super().save(*args, **kwargs)

    def __str__(self):
        return f'Application {self.pk}: {self.applicant_name}'
