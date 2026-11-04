import tempfile

from django.core.files.base import ContentFile
from django.http import Http404
from django.test import RequestFactory, TestCase, override_settings

from .media import public_brand_image
from .models import FirmProfile


class HostedBrandImageTests(TestCase):
    def test_only_referenced_images_can_be_downloaded_and_missing_is_404(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            profile = FirmProfile.objects.create(name='Fictional firm')
            profile.logo.save('test.png', ContentFile(b'fictional-image-fixture'))
            request = RequestFactory().get('/media/' + profile.logo.name)
            response = public_brand_image(request, profile.logo.name)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'image/png')
            # Direct view invocation: close the file without emitting the HTTP
            # request_finished signal inside TestCase's database transaction.
            response.file_to_stream.close()
            for name in ('../private_media/secret.txt', 'unreferenced.png', 'private_media/secret.txt'):
                with self.assertRaises(Http404):
                    public_brand_image(request, name)
            profile.logo.storage.delete(profile.logo.name)
            with self.assertRaises(Http404):
                public_brand_image(request, profile.logo.name)
