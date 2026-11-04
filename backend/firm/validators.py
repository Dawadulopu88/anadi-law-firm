from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_brand_image_size(file):
    if file.size > 5 * 1024 * 1024:
        raise ValidationError(_('Images must be 5 MB or smaller.'))
