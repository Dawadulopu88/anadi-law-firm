from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models, router, transaction
from django.utils.translation import gettext_lazy as _

from accounts.permissions import has_role


class ConsultationRequest(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', _('New')
        CONTACTED = 'contacted', _('Contacted')
        CONVERTED = 'converted', _('Converted')
        CLOSED = 'closed', _('Closed')

    class Language(models.TextChoices):
        ENGLISH = 'en', _('English')
        BANGLA = 'bn', _('Bangla')

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    practice_area = models.ForeignKey('firm.PracticeArea', on_delete=models.PROTECT, related_name='consultation_requests')
    message = models.TextField(max_length=5000)
    preferred_date = models.DateField(null=True, blank=True)
    preferred_language = models.CharField(max_length=2, choices=Language.choices, default=Language.ENGLISH)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NEW)
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='handled_consultations')
    client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, null=True, blank=True, related_name='consultation_requests')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(status='converted', client__isnull=False)
                           | (~models.Q(status='converted') & models.Q(client__isnull=True))),
                name='intake_conversion_client_consistent',
            ),
        ]

    def clean(self):
        super().clean()
        if (self.status == self.Status.CONVERTED) != (self.client_id is not None):
            raise ValidationError({'status': _('Use the conversion action to link a client.')})

    def save(self, *args, **kwargs):
        using = kwargs.get('using') or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=using):
            if self.pk:
                previous = type(self).objects.using(using).select_for_update().filter(pk=self.pk).first()
                if previous and previous.status == self.Status.CONVERTED:
                    if self.status != previous.status or self.client_id != previous.client_id:
                        raise ValidationError({'status': _('A converted request cannot be unlinked or reopened.')})
            self.full_clean()
            return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.get_status_display()})'


class Appointment(models.Model):
    class Type(models.TextChoices):
        CONSULTATION = 'consultation', _('Consultation')
        MEETING = 'meeting', _('Meeting')
        CALL = 'call', _('Call')

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', _('Scheduled')
        COMPLETED = 'completed', _('Completed')
        CANCELLED = 'cancelled', _('Cancelled')

    client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='appointments')
    case = models.ForeignKey('cases.Case', on_delete=models.PROTECT, null=True, blank=True, related_name='appointments')
    lawyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='appointments', limit_choices_to={'role': 'lawyer'},
    )
    start = models.DateTimeField()
    end = models.DateTimeField()
    appointment_type = models.CharField(max_length=12, choices=Type.choices, default=Type.CONSULTATION)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SCHEDULED)
    notes = models.TextField(blank=True, max_length=5000, help_text=_('Internal notes; not visible to clients.'))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_appointments', editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start', 'pk']
        indexes = [models.Index(fields=['lawyer', 'status', 'start'], name='intake_lawyer_schedule_idx')]
        constraints = [models.CheckConstraint(condition=models.Q(end__gt=models.F('start')), name='intake_appointment_positive_duration')]

    def clean(self):
        super().clean()
        errors = {}
        if self.case_id and self.client_id and self.case.client_id != self.client_id:
            errors['case'] = _('The case must belong to the appointment client.')
        if self.start and self.end and self.end <= self.start:
            errors['end'] = _('End must be after start.')
        if self.lawyer_id:
            previous_lawyer = None
            if self.pk:
                previous_lawyer = type(self).objects.filter(pk=self.pk).values_list('lawyer_id', flat=True).first()
            must_be_active = self.status == self.Status.SCHEDULED or previous_lawyer != self.lawyer_id
            if must_be_active and not has_role(self.lawyer, 'lawyer'):
                errors['lawyer'] = _('Choose an active lawyer.')
        if self.client_id and self.status == self.Status.SCHEDULED and self.client.status != 'active':
            errors['client'] = _('Scheduled appointments require an active client record.')
        if not errors and self.status == self.Status.SCHEDULED and self.lawyer_id and self.start and self.end:
            # Adjacent intervals are allowed; only a strict intersection conflicts.
            conflicts = type(self).objects.filter(
                lawyer_id=self.lawyer_id, status=self.Status.SCHEDULED,
                start__lt=self.end, end__gt=self.start,
            ).exclude(pk=self.pk)
            if conflicts.exists():
                errors['start'] = _('This lawyer already has an overlapping appointment.')
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        using = kwargs.get('using') or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=using):
            lawyer_ids = {self.lawyer_id} if self.lawyer_id else set()
            if self.pk:
                old = type(self).objects.using(using).filter(pk=self.pk).values_list('lawyer_id', flat=True).first()
                if old:
                    lawyer_ids.add(old)
            # All supported writes (API and Admin) serialize on the lawyer rows.
            # Sorting keeps reassignments from locking lawyer rows in opposite orders.
            list(get_user_model().objects.using(using).select_for_update().filter(
                pk__in=lawyer_ids,
            ).order_by('pk'))
            self.full_clean()
            return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.client} - {self.start}'
