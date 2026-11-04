from tempfile import TemporaryDirectory
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from cases.tests import CaseFixtures
from .models import Document


class DocumentTests(CaseFixtures):
    def setUp(self):
        super().setUp()
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings_override = override_settings(PRIVATE_MEDIA_ROOT=self.tmp.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.login(self.staff)

    def upload(self, **kwargs):
        data = {'case': self.case.pk, 'title': 'Sample', 'document_type': 'note', 'file': SimpleUploadedFile('sample.txt', b'Confidential sample')}
        data.update(kwargs)
        return self.api.post('/api/documents/', data, format='multipart')

    def test_upload_private_download_and_safe_metadata(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn('file', response.data)
        doc = Document.objects.get(pk=response.data['id'])
        with self.assertRaises(ValueError):
            _ = doc.file.url
        response = self.api.get(f'/api/documents/{doc.pk}/download/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'Confidential sample')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_client_private_and_other_client_download_denied(self):
        doc_id = self.upload().data['id']
        path = f'/api/documents/{doc_id}/download/'
        self.login(self.owner)
        self.assertEqual(self.api.get(path).status_code, 404)
        self.assertEqual(self.results('/api/documents/'), [])
        self.login(self.staff)
        self.assertEqual(self.api.patch(f'/api/documents/{doc_id}/', {'is_client_visible': True}, format='json').status_code, 200)
        self.login(self.owner)
        response = self.api.get(path)
        self.assertEqual(response.status_code, 200)
        b''.join(response.streaming_content)
        self.login(self.outsider)
        self.assertEqual(self.api.get(path).status_code, 404)

    def test_lawyer_assignment_and_anonymous_access(self):
        doc_id = self.upload().data['id']
        self.login(self.other_lawyer)
        self.assertEqual(self.api.get(f'/api/documents/{doc_id}/download/').status_code, 404)
        self.assertEqual(self.upload().status_code, 400)
        self.api.force_authenticate(None)
        self.assertEqual(self.api.get(f'/api/documents/{doc_id}/download/').status_code, 401)

    def test_direct_media_paths_not_served(self):
        doc = Document.objects.get(pk=self.upload().data['id'])
        self.api.force_authenticate(None)
        for prefix in ('/media/', '/private_media/'):
            self.assertEqual(self.api.get(prefix + doc.file.name).status_code, 404)

    def test_invalid_formats_signatures_size_and_version(self):
        for filename, data in [('x.exe', b'MZ'), ('x.pdf', b'Not PDF'), ('x.png', b'Not PNG'), ('x.txt', b'\xff\x00'), ('x.txt', b'x' * (10 * 1024 * 1024 + 1))]:
            with self.subTest(filename=filename, size=len(data)):
                self.assertEqual(self.upload(file=SimpleUploadedFile(filename, data)).status_code, 400)
        self.assertEqual(self.upload(version=0).status_code, 400)
        self.assertEqual(Document.objects.count(), 0)

    def test_valid_image_and_pdf_uploads(self):
        image = BytesIO()
        Image.new('RGB', (2, 2)).save(image, format='PNG')
        for name, data in [('image.png', image.getvalue()), ('sample.pdf', b'%PDF-1.4\n%%EOF')]:
            response = self.upload(file=SimpleUploadedFile(name, data))
            self.assertEqual(response.status_code, 201, response.data)

    def test_file_and_case_not_replaceable(self):
        doc_id = self.upload().data['id']
        path = f'/api/documents/{doc_id}/'
        self.assertEqual(self.api.patch(path, {'file': SimpleUploadedFile('other.txt', b'Other')}, format='multipart').status_code, 400)
        self.assertEqual(self.api.patch(path, {'case': self.other_case.pk}, format='json').status_code, 400)
        self.assertEqual(self.api.delete(path).status_code, 405)

    def test_put_updates_metadata_without_requiring_or_replacing_file(self):
        document = Document.objects.get(pk=self.upload().data['id'])
        original_path = document.file.name
        path = f'/api/documents/{document.pk}/'
        payload = {'case': self.case.pk, 'title': 'Updated title', 'document_type': 'note', 'version': 1}
        response = self.api.put(path, payload, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        document.refresh_from_db()
        self.assertEqual(document.file.name, original_path)
        self.assertEqual(document.title, 'Updated title')
        payload['file'] = SimpleUploadedFile('replacement.txt', b'Replacement')
        self.assertEqual(self.api.put(path, payload, format='multipart').status_code, 400)

    def test_admin_view_does_not_generate_public_url(self):
        doc_id = self.upload().data['id']
        self.client.force_login(self.admin_user)
        self.assertEqual(self.client.get(f'/admin/documents/document/{doc_id}/change/').status_code, 200)
        response = self.client.get(f'/admin/documents/document/{doc_id}/download/')
        self.assertEqual(response.status_code, 200)
        b''.join(response.streaming_content)
