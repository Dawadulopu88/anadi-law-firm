from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction

from cases.models import ValidatedModel


class Timestamped(ValidatedModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Jurisdiction(Timestamped):
    name = models.CharField(max_length=100)
    name_bn = models.CharField(max_length=100, blank=True)
    code = models.SlugField(max_length=20, unique=True)
    flag = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ['name', 'pk']

    def __str__(self):
        return self.name


class RightsTopic(Timestamped):
    title = models.CharField(max_length=150)
    title_bn = models.CharField(max_length=150, blank=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    description_bn = models.TextField(blank=True)
    practice_area = models.ForeignKey('firm.PracticeArea', on_delete=models.PROTECT, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['title', 'pk']

    def __str__(self):
        return self.title


class ReviewedContent(Timestamped):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        REVIEWED = 'reviewed', 'Reviewed'
        PUBLISHED = 'published', 'Published'

    jurisdiction = models.ForeignKey(Jurisdiction, on_delete=models.PROTECT)
    topic = models.ForeignKey(RightsTopic, on_delete=models.PROTECT)
    language = models.CharField(max_length=2, choices=[('en', 'English'), ('bn', 'Bangla')], default='en')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    is_sample = models.BooleanField(default=False)
    review_fields = ('jurisdiction_id', 'topic_id', 'language', 'is_sample')

    class Meta:
        abstract = True
        ordering = ['-created_at', '-pk']

    def clean(self):
        super().clean()
        if self.status != self.Status.DRAFT and (not self.reviewed_by_id or not self.reviewed_at):
            raise ValidationError({'status': 'Review this content before publishing.'})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            old = type(self).objects.select_for_update().filter(pk=self.pk).first() if self.pk else None
            if old and any(getattr(old, f) != getattr(self, f) for f in self.review_fields):
                self.status, self.reviewed_by, self.reviewed_at = 'draft', None, None
                if kwargs.get('update_fields'):
                    kwargs['update_fields'] = set(kwargs['update_fields']) | {'status', 'reviewed_by', 'reviewed_at'}
            return super().save(*args, **kwargs)


class KnowledgeArticle(ReviewedContent):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    summary = models.TextField(max_length=2000)
    body = models.TextField(max_length=50000)
    source_reference = models.TextField(max_length=2000)
    review_fields = ReviewedContent.review_fields + ('title', 'slug', 'summary', 'body', 'source_reference')

    def __str__(self):
        return self.title


class FAQ(ReviewedContent):
    question = models.CharField(max_length=500)
    answer = models.TextField(max_length=10000)
    review_fields = ReviewedContent.review_fields + ('question', 'answer')

    def __str__(self):
        return self.question


class HelpContact(Timestamped):
    label = models.CharField(max_length=150)
    label_bn = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30)
    hours = models.CharField(max_length=200)
    hours_bn = models.CharField(max_length=200, blank=True)
    is_emergency = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    verification_reference = models.CharField(max_length=500, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['display_order', 'pk']

    def save(self, *args, **kwargs):
        if self.pk:
            old = type(self).objects.get(pk=self.pk)
            fields = ('label', 'label_bn', 'phone', 'hours', 'hours_bn', 'is_emergency', 'verification_reference')
            if any(getattr(old, f) != getattr(self, f) for f in fields):
                self.verified_by, self.verified_at = None, None
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.label


class GuidedFlow(Timestamped):
    name = models.CharField(max_length=200)
    name_bn = models.CharField(max_length=200, blank=True)
    purpose = models.CharField(max_length=15, choices=[('issue_finder', 'Issue finder'), ('eligibility', 'Indicative eligibility')])
    start_question = models.ForeignKey('GuidedQuestion', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    is_active = models.BooleanField(default=False)
    is_sample = models.BooleanField(default=True)

    class Meta:
        ordering = ['pk']

    def clean(self):
        super().clean()
        if self.start_question_id and self.start_question.flow_id != self.pk:
            raise ValidationError({'start_question': 'Start question must belong to this flow.'})
        if self.is_active:
            from .guided import validate_flow
            validate_flow(self)

    def __str__(self):
        return self.name


class GuidedQuestion(Timestamped):
    flow = models.ForeignKey(GuidedFlow, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=500)
    text_bn = models.CharField(max_length=500, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'pk']

    def save(self, *args, **kwargs):
        with transaction.atomic():
            GuidedFlow.objects.select_for_update().get(pk=self.flow_id)
            if self.pk and type(self).objects.filter(pk=self.pk).exclude(flow_id=self.flow_id).exists():
                raise ValidationError('Questions cannot be moved between flows.')
            result = super().save(*args, **kwargs)
            GuidedFlow.objects.filter(pk=self.flow_id).update(is_active=False)
            return result

    def __str__(self):
        return self.text


class GuidedOption(Timestamped):
    question = models.ForeignKey(GuidedQuestion, on_delete=models.CASCADE, related_name='options')
    label = models.CharField(max_length=200)
    label_bn = models.CharField(max_length=200, blank=True)
    next_question = models.ForeignKey(GuidedQuestion, on_delete=models.PROTECT, null=True, blank=True, related_name='incoming_options')
    outcome_practice_area = models.ForeignKey('firm.PracticeArea', on_delete=models.PROTECT, null=True, blank=True)
    outcome_article = models.ForeignKey(KnowledgeArticle, on_delete=models.PROTECT, null=True, blank=True)
    escalate_to_consultation = models.BooleanField(default=False)

    class Meta:
        ordering = ['pk']

    def clean(self):
        super().clean()
        has_result = bool(self.outcome_practice_area_id or self.outcome_article_id or self.escalate_to_consultation)
        if bool(self.next_question_id) == has_result:
            raise ValidationError('Choose either a next question or at least one outcome, never both.')
        if self.next_question_id and self.question_id and self.next_question.flow_id != self.question.flow_id:
            raise ValidationError({'next_question': 'Next question must be in the same flow.'})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            flow_id = self.question.flow_id
            GuidedFlow.objects.select_for_update().get(pk=flow_id)
            if self.pk and type(self).objects.filter(pk=self.pk).exclude(question_id=self.question_id).exists():
                raise ValidationError('Options cannot be moved between questions.')
            result = super().save(*args, **kwargs)
            GuidedFlow.objects.filter(pk=flow_id).update(is_active=False)
            return result

    def __str__(self):
        return self.label
