from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from accounts.permissions import has_role


def public_content(model):
    return model.objects.filter(status='published', reviewed_by__isnull=False,
                                reviewed_at__isnull=False, jurisdiction__is_active=True,
                                topic__is_active=True).select_related('jurisdiction', 'topic')


def review_content(model, pk, user, publish=False):
    if not has_role(user, 'admin', 'lawyer') or not user.has_perm(f'knowledge.change_{model._meta.model_name}'):
        raise PermissionDenied('An authorized reviewer is required.')
    with transaction.atomic():
        item = model.objects.select_for_update().get(pk=pk)
        if publish:
            if item.status != 'reviewed' or not item.reviewed_at or not item.reviewed_by_id:
                raise ValidationError('Review the current content before publishing.')
            item.status = 'published'
        else:
            item.status, item.reviewed_by, item.reviewed_at = 'reviewed', user, timezone.now()
        item.save()
        return item
