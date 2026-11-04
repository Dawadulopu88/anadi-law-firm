from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.permissions import has_role


class ValidatedModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Case(ValidatedModel):
    class Status(models.TextChoices):
        OPEN = 'open', _('Open')
        IN_PROGRESS = 'in_progress', _('In progress')
        ON_HOLD = 'on_hold', _('On hold')
        CLOSED = 'closed', _('Closed')
        ARCHIVED = 'archived', _('Archived')

    case_number = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True, max_length=10000, help_text=_('Client-visible summary. Put confidential staff discussions in internal notes.'))
    client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='cases')
    practice_area = models.ForeignKey('firm.PracticeArea', on_delete=models.PROTECT, related_name='cases')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    filing_date = models.DateField(null=True, blank=True)
    court = models.CharField(max_length=200, blank=True)
    opposite_party = models.CharField(max_length=250, blank=True)
    priority = models.CharField(max_length=10, choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High')], default='normal')
    closed_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_cases', editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        indexes = [models.Index(fields=['status', 'practice_area'], name='cases_status_area_idx')]

    def clean(self):
        super().clean()
        if self.closed_date:
            if self.status not in ('closed', 'archived'):
                raise ValidationError({'closed_date': 'Only closed or archived cases can have a closed date.'})
            if self.filing_date and self.closed_date < self.filing_date:
                raise ValidationError({'closed_date': 'Closed date cannot be before filing date.'})
        if self.pk:
            old = type(self).objects.filter(pk=self.pk).values('client_id').first()
            if old and old['client_id'] != self.client_id:
                raise ValidationError({'client': _('A case cannot be transferred to another client. Create a separate case instead.')})
        elif self.client_id and self.client.status != 'active':
            raise ValidationError({'client': _('Choose an active client for a new case.')})
        if self.practice_area_id and not self.practice_area.is_active:
            unchanged = self.pk and type(self).objects.filter(pk=self.pk, practice_area_id=self.practice_area_id).exists()
            if not unchanged:
                raise ValidationError({'practice_area': _('Choose an active practice area.')})

    def __str__(self):
        return f'{self.case_number} — {self.title}'


class CaseAssignment(ValidatedModel):
    case = models.ForeignKey(Case, on_delete=models.PROTECT, related_name='assignments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='case_assignments', limit_choices_to={'role__in': ['lawyer', 'staff']})
    role = models.CharField(max_length=10, choices=[('lead', 'Lead'), ('support', 'Support')], default='support')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='made_case_assignments', editable=False)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['assigned_at', 'pk']
        constraints = [models.UniqueConstraint(fields=['case', 'user'], name='cases_unique_assignment')]

    def clean(self):
        super().clean()
        if self.user_id and not has_role(self.user, 'lawyer', 'staff'):
            raise ValidationError({'user': _('Choose an active lawyer or staff member.')})
        if self.pk and type(self).objects.filter(pk=self.pk).exclude(case_id=self.case_id, user_id=self.user_id).exists():
            raise ValidationError(_('Remove the assignment and create a new one instead.'))

    def __str__(self):
        return f'{self.case} — {self.user} ({self.role})'


class CaseNote(ValidatedModel):
    case = models.ForeignKey(Case, on_delete=models.PROTECT, related_name='notes')
    body = models.TextField(max_length=10000)
    is_internal = models.BooleanField(default=True, help_text=_('Uncheck only for notes intended to be shared with the client.'))
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='case_notes', editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']

    def clean(self):
        super().clean()
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError(_('Notes are permanent. Add a correction as a new note.'))

    def __str__(self):
        return f'Note {self.pk} for {self.case.case_number}'


class Hearing(ValidatedModel):
    case = models.ForeignKey(Case, on_delete=models.PROTECT, related_name='hearings')
    court_name = models.CharField(max_length=200)
    hearing_at = models.DateTimeField()
    case_number = models.CharField(max_length=100, blank=True)
    outcome = models.TextField(blank=True, max_length=5000)
    next_hearing_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['hearing_at', 'pk']

    def clean(self):
        super().clean()
        if self.next_hearing_date and self.hearing_at and self.next_hearing_date <= self.hearing_at:
            raise ValidationError({'next_hearing_date': 'Next hearing must be later than this hearing.'})
        if self.pk and type(self).objects.filter(pk=self.pk).exclude(case_id=self.case_id).exists():
            raise ValidationError({'case': 'A hearing cannot be moved to another case.'})

    def __str__(self):
        return f'{self.case} — {self.hearing_at}'


class Task(ValidatedModel):
    case = models.ForeignKey(Case, on_delete=models.PROTECT, null=True, blank=True, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, max_length=10000)
    priority = models.CharField(max_length=10, choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High')], default='normal')
    due_date = models.DateField()
    status = models.CharField(max_length=12, choices=[('pending', 'Pending'), ('in_progress', 'In progress'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='pending')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='assigned_tasks')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, editable=False, related_name='created_tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', 'pk']

    def clean(self):
        super().clean()
        if self.assigned_to_id:
            from accounts.permissions import is_firm_member
            if not is_firm_member(self.assigned_to):
                raise ValidationError({'assigned_to': 'Choose an active firm member.'})
            if self.case_id and has_role(self.assigned_to, 'lawyer') and not self.case.assignments.filter(user_id=self.assigned_to_id).exists():
                raise ValidationError({'assigned_to': 'The lawyer must be assigned to this case.'})
        if self.pk and type(self).objects.filter(pk=self.pk).exclude(case_id=self.case_id).exists():
            raise ValidationError({'case': 'A task cannot be moved to another case.'})

    def __str__(self):
        return self.title
