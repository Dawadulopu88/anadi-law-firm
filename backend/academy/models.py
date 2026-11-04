from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from knowledge.models import Timestamped


class Pathway(Timestamped):
    title = models.CharField(max_length=200)
    title_bn = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True, max_length=5000)
    description_bn = models.TextField(blank=True, max_length=5000)
    is_active = models.BooleanField(default=True)
    is_sample = models.BooleanField(default=False)

    class Meta:
        ordering = ['title', 'pk']

    def __str__(self):
        return self.title


class Course(Timestamped):
    pathway = models.ForeignKey(Pathway, on_delete=models.PROTECT, related_name='courses')
    title = models.CharField(max_length=200)
    title_bn = models.CharField(max_length=200, blank=True)
    summary = models.TextField(max_length=5000)
    summary_bn = models.TextField(blank=True, max_length=5000)
    level = models.CharField(max_length=15, choices=[('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced')], default='beginner')
    duration = models.CharField(max_length=100)
    duration_bn = models.CharField(max_length=100, blank=True)
    instructor = models.CharField(max_length=200)
    is_published = models.BooleanField(default=False)
    is_sample = models.BooleanField(default=False)

    class Meta:
        ordering = ['title', 'pk']

    def __str__(self):
        return self.title


class LiveSession(Timestamped):
    title = models.CharField(max_length=200)
    title_bn = models.CharField(max_length=200, blank=True)
    course = models.ForeignKey(Course, on_delete=models.PROTECT, null=True, blank=True, related_name='sessions')
    start = models.DateTimeField()
    end = models.DateTimeField()
    venue = models.CharField(max_length=300, blank=True)
    venue_bn = models.CharField(max_length=300, blank=True)
    meeting_link = models.URLField(blank=True)
    capacity = models.PositiveIntegerField()
    is_published = models.BooleanField(default=False)
    is_sample = models.BooleanField(default=False)

    class Meta:
        ordering = ['start', 'pk']
        constraints = [models.CheckConstraint(condition=models.Q(end__gt=models.F('start')), name='academy_positive_session_duration'),
                       models.CheckConstraint(condition=models.Q(capacity__gt=0), name='academy_positive_capacity')]

    @property
    def seats_remaining(self):
        return max(0, (self.capacity or 0) - (self.registrations.count() if self.pk else 0))

    @property
    def registration_open(self):
        return self.is_published and self.start > timezone.now() and (
            not self.course_id or (self.course.is_published and self.course.pathway.is_active)
        )

    def clean(self):
        super().clean()
        errors = {}
        if self.start and self.end and self.end <= self.start:
            errors['end'] = 'End must be after start.'
        if self.capacity is not None and (self.capacity < 1 or (self.pk and self.capacity < self.registrations.count())):
            errors['capacity'] = 'Capacity must be positive and cannot be below existing registrations.'
        if not self.venue.strip() and not self.meeting_link:
            errors['venue'] = 'Provide a venue or meeting link.'
        if self.meeting_link and not self.meeting_link.startswith('https://'):
            errors['meeting_link'] = 'Meeting links must use HTTPS.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.pk:
                type(self).objects.select_for_update().get(pk=self.pk)
            return super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class SessionRegistration(Timestamped):
    session = models.ForeignKey(LiveSession, on_delete=models.PROTECT, related_name='registrations')
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='session_registrations')

    class Meta:
        ordering = ['created_at', 'pk']
        constraints = [models.UniqueConstraint(fields=['session', 'email'], name='academy_unique_session_email')]

    def clean(self):
        super().clean()
        if self.pk and type(self).objects.filter(pk=self.pk).exclude(session_id=self.session_id).exists():
            raise ValidationError({'session': 'Registrations cannot be moved to another session.'})
        if self.session_id:
            if self._state.adding and not self.session.registration_open:
                raise ValidationError({'session': 'Registration is closed for this session.'})
            if self.session.registrations.exclude(pk=self.pk).count() >= self.session.capacity:
                raise ValidationError({'session': 'This session is full.'})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            self.email = self.email.strip().lower()
            # Session edits and all registrations serialize on this parent row.
            self.session = LiveSession.objects.select_for_update().get(pk=self.session_id)
            return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            LiveSession.objects.select_for_update().get(pk=self.session_id)
            return super().delete(*args, **kwargs)

    def __str__(self):
        return f'{self.session} — {self.name}'
