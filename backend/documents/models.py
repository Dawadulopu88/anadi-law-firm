from pathlib import Path
from uuid import uuid4
from PIL import Image
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from cases.models import ValidatedModel
from .storage import private_storage


def private_path(instance, filename):
    return f'cases/{instance.case_id}/{uuid4().hex}{Path(filename).suffix.lower()}'


def validate_document(file):
    # Stored files are immutable and were checked on upload. Metadata updates
    # must not reopen them (or leave filesystem handles open on Windows).
    if getattr(file, '_committed', False):
        return
    if not file.size or file.size > 10 * 1024 * 1024:
        raise ValidationError('Upload a non-empty file no larger than 10 MB.')
    suffix = Path(file.name).suffix.lower()
    if suffix not in {'.pdf', '.png', '.jpg', '.jpeg', '.txt'}:
        raise ValidationError('Allowed formats: PDF, PNG, JPEG and UTF-8 TXT.')
    try:
        file.seek(0)
        if suffix == '.pdf':
            if file.read(5) != b'%PDF-':
                raise ValueError
        elif suffix in {'.png', '.jpg', '.jpeg'}:
            with Image.open(file) as img:
                if img.format != ('PNG' if suffix == '.png' else 'JPEG'):
                    raise ValueError
                img.verify()
        else:
            data = file.read().decode('utf-8')
            if '\x00' in data:
                raise ValueError
    except (ValueError, OSError, UnicodeError, Image.DecompressionBombError):
        raise ValidationError('File contents do not match the selected format.')
    finally:
        file.seek(0)


class Document(ValidatedModel):
    case = models.ForeignKey('cases.Case', on_delete=models.PROTECT, related_name='documents')
    title = models.CharField(max_length=200)
    document_type = models.CharField(max_length=80)
    file = models.FileField(storage=private_storage, upload_to=private_path, validators=[validate_document])
    version = models.PositiveIntegerField(default=1)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='uploaded_documents', editable=False)
    is_client_visible = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at', '-pk']
        constraints = [models.CheckConstraint(condition=models.Q(version__gte=1), name='documents_positive_version')]

    def clean(self):
        super().clean()
        if self.version < 1:
            raise ValidationError({'version': 'Version must be at least one.'})
        if self.pk:
            old = type(self).objects.filter(pk=self.pk).first()
            if old and (old.case_id != self.case_id or old.file.name != self.file.name or not self.file._committed):
                raise ValidationError('Case and file cannot be replaced; upload a new document version.')

    def save(self, *args, **kwargs):
        new_upload = not self.file._committed
        try:
            return super().save(*args, **kwargs)
        except Exception:
            if new_upload and self.file._committed:
                self.file.storage.delete(self.file.name)
            raise

    def __str__(self):
        return self.title
