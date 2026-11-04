"""Small-demo branding delivery without exposing a whole upload directory."""
from pathlib import PurePosixPath

from django.http import FileResponse, Http404
from django.views.decorators.http import require_safe

from .models import FirmProfile, LawyerProfile


@require_safe
def public_brand_image(request, name):
    # Only an exact database reference to a currently public image is served.
    # This route never consults PRIVATE_MEDIA_ROOT or accepts arbitrary files.
    parts = PurePosixPath(name).parts
    if '..' in parts or '\\' in name or name.startswith('/'):
        raise Http404
    profile = FirmProfile.objects.filter(logo=name).first()
    field = profile.logo if profile and profile.logo else None
    if field is None:
        lawyer = LawyerProfile.objects.filter(photo=name, is_public=True,
                    user__is_active=True, user__role='lawyer').first()
        field = lawyer.photo if lawyer and lawyer.photo else None
    content_type = {'.png': 'image/png', '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg', '.webp': 'image/webp'}.get(PurePosixPath(name).suffix.lower())
    if field is None or content_type is None:
        raise Http404
    try:
        response = FileResponse(field.open('rb'), content_type=content_type)
    except (FileNotFoundError, OSError):
        raise Http404 from None
    response['Cache-Control'] = 'no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
