from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .validators import validate_brand_image_size


def image_validators():
    return [
        FileExtensionValidator(['png', 'jpg', 'jpeg', 'webp']),
        validate_brand_image_size,
    ]


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class FirmProfile(TimestampedModel):
    # The database enforces the one-row profile, including outside Admin.
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    name = models.CharField(max_length=160)
    name_bn = models.CharField(max_length=160, blank=True)
    tagline = models.CharField(max_length=250, blank=True)
    tagline_bn = models.CharField(max_length=250, blank=True)
    about = models.TextField(blank=True)
    about_bn = models.TextField(blank=True)
    address = models.TextField(blank=True)
    address_bn = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    logo = models.ImageField(upload_to='firm/logos/', blank=True, validators=image_validators())
    working_hours = models.CharField(max_length=250, blank=True)
    working_hours_bn = models.CharField(max_length=250, blank=True)
    website_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)

    class Meta:
        verbose_name_plural = 'Firm profile'
        constraints = [
            models.CheckConstraint(condition=models.Q(id=1), name='firm_profile_single_row'),
        ]

    def __str__(self):
        return self.name


class PracticeArea(TimestampedModel):
    name = models.CharField(max_length=120)
    name_bn = models.CharField(max_length=120, blank=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    description_bn = models.TextField(blank=True)
    # Frontend icon identifier, not HTML.
    icon = models.CharField(max_length=80, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order', 'name', 'pk']

    def __str__(self):
        return self.name


class LawyerProfile(TimestampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='lawyer_profile', limit_choices_to={'role': 'lawyer'},
    )
    full_name_bn = models.CharField(max_length=300, blank=True)
    photo = models.ImageField(upload_to='firm/lawyers/', blank=True, validators=image_validators())
    title = models.CharField(max_length=160)
    title_bn = models.CharField(max_length=160, blank=True)
    bio = models.TextField(blank=True)
    bio_bn = models.TextField(blank=True)
    practice_areas = models.ManyToManyField(PracticeArea, related_name='lawyers', blank=True)
    experience_years = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(80)])
    languages = models.CharField(max_length=200, default='English, Bangla')
    languages_bn = models.CharField(max_length=200, blank=True)
    is_public = models.BooleanField(default=False)

    class Meta:
        ordering = ['pk']

    def clean(self):
        super().clean()
        if self.user_id and self.user.role != 'lawyer':
            raise ValidationError({'user': _('Choose a user with the lawyer role.')})

    def __str__(self):
        return self.user.get_full_name() or self.user.username
