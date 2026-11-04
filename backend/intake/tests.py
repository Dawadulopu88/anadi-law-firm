from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections, connections, transaction
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient

from clients.models import Client
from firm.models import PracticeArea
from .models import Appointment, ConsultationRequest
from .services import convert_consultation
from .throttles import ConsultationBurstThrottle, ConsultationDailyThrottle

User = get_user_model()


class IntakeFixtures(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser(username='admin', password='Test-only-admin-481!')
        cls.staff = User.objects.create_user(username='staff', role='staff')
        cls.lawyer = User.objects.create_user(username='lawyer', role='lawyer', first_name='Demo', last_name='Lawyer')
        cls.other_lawyer = User.objects.create_user(username='lawyer_two', role='lawyer')
        cls.one_user = User.objects.create_user(username='client_one', role='client')
        cls.two_user = User.objects.create_user(username='client_two', role='client')
        cls.one = Client.objects.create(full_name='Client One', user=cls.one_user, created_by=cls.admin_user)
        cls.two = Client.objects.create(full_name='Client Two', user=cls.two_user, created_by=cls.admin_user)
        cls.area = PracticeArea.objects.create(name='Family Law', slug='family-law')
        cls.hidden_area = PracticeArea.objects.create(name='Hidden', slug='hidden', is_active=False)
        cls.start = timezone.now().replace(microsecond=0) + timedelta(days=2)
        cls.end = cls.start + timedelta(hours=1)

    def setUp(self):
        cache.clear()
        self.api = APIClient()

    def consultation(self, **changes):
        fields = dict(name='Sample Visitor', phone='01700000000', email='visitor@example.test',
                      practice_area=self.area, message='Private demo request', preferred_language='bn')
        fields.update(changes)
        return ConsultationRequest.objects.create(**fields)

    def public_payload(self, **changes):
        data = dict(name='Sample Visitor', phone='01700000000', email='visitor@example.test',
                    practice_area=self.area.pk, message='Private demo request', preferred_language='bn',
                    preferred_date=str(timezone.localdate() + timedelta(days=1)), website='')
        data.update(changes)
        return data

    def appointment(self, **changes):
        fields = dict(client=self.one, lawyer=self.lawyer, start=self.start, end=self.end,
                      notes='Internal appointment note', created_by=self.admin_user)
        fields.update(changes)
        return Appointment.objects.create(**fields)

    def appointment_payload(self, **changes):
        data = dict(client=self.one.pk, lawyer=self.lawyer.pk, start=self.start.isoformat(),
                    end=self.end.isoformat(), appointment_type='consultation', notes='Internal appointment note')
        data.update(changes)
        return data


class ConsultationAPITests(IntakeFixtures):
    def test_anonymous_submission_has_minimal_receipt_and_safe_defaults(self):
        response = self.api.post('/api/consultations/', self.public_payload(
            status='converted', client=self.two.pk, handled_by=self.staff.pk,
        ), format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.data), {'id', 'status'})
        item = ConsultationRequest.objects.get(pk=response.data['id'])
        self.assertEqual(item.status, 'new')
        self.assertIsNone(item.client)
        self.assertIsNone(item.handled_by)
        self.assertEqual(item.preferred_language, 'bn')

    def test_contact_and_message_fields_are_validated(self):
        for changes in [{'name': ''}, {'phone': ''}, {'email': 'invalid'}, {'message': ''}, {'message': 'x' * 5001}]:
            response = self.api.post('/api/consultations/', self.public_payload(**changes), format='json')
            self.assertEqual(response.status_code, 400)
        self.assertEqual(ConsultationRequest.objects.count(), 0)

    def test_inactive_practice_area_is_rejected(self):
        self.assertEqual(self.api.post('/api/consultations/', self.public_payload(practice_area=self.hidden_area.pk), format='json').status_code, 400)

    def test_past_date_and_invalid_language_rejected(self):
        for changes in [{'preferred_date': str(timezone.localdate() - timedelta(days=1))}, {'preferred_language': 'xx'}]:
            self.assertEqual(self.api.post('/api/consultations/', self.public_payload(**changes), format='json').status_code, 400)

    def test_optional_email_and_date_can_be_omitted(self):
        data = self.public_payload()
        data.pop('email')
        data.pop('preferred_date')
        self.assertEqual(self.api.post('/api/consultations/', data, format='json').status_code, 201)

    def test_honeypot_rejects_bot_submission(self):
        self.assertEqual(self.api.post('/api/consultations/', self.public_payload(website='https://spam.example'), format='json').status_code, 400)
        self.assertEqual(ConsultationRequest.objects.count(), 0)

    def test_burst_rate_limit_returns_429_and_retry_after(self):
        with patch.object(ConsultationBurstThrottle, 'rate', '2/min', create=True):
            responses = [self.api.post('/api/consultations/', self.public_payload(), format='json') for _ in range(3)]
        self.assertEqual([r.status_code for r in responses], [201, 201, 429])
        self.assertIn('Retry-After', responses[-1].headers)
        self.assertEqual(ConsultationRequest.objects.count(), 2)

    def test_daily_rate_limit_applies_even_to_authenticated_submitter(self):
        self.api.force_authenticate(self.one_user)
        with patch.object(ConsultationDailyThrottle, 'rate', '1/day', create=True):
            self.assertEqual(self.api.post('/api/consultations/', self.public_payload(), format='json').status_code, 201)
            self.assertEqual(self.api.post('/api/consultations/', self.public_payload(), format='json').status_code, 429)

    def test_untrusted_forwarded_header_cannot_bypass_local_throttle(self):
        with patch.object(ConsultationBurstThrottle, 'rate', '1/min', create=True):
            first = self.api.post('/api/consultations/', self.public_payload(), format='json', HTTP_X_FORWARDED_FOR='192.0.2.1')
            second = self.api.post('/api/consultations/', self.public_payload(), format='json', HTTP_X_FORWARDED_FOR='192.0.2.2')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 429)

    def test_visitors_cannot_read_or_manage_submissions(self):
        item = self.consultation()
        for actor, expected in [(None, 401), (self.one_user, 403)]:
            self.api.force_authenticate(actor)
            for method, url in [('get', '/api/consultations/'), ('get', f'/api/consultations/{item.pk}/'),
                                ('patch', f'/api/consultations/{item.pk}/'), ('post', f'/api/consultations/{item.pk}/convert/')]:
                response = getattr(self.api, method)(url) if method == 'get' else getattr(self.api, method)(url, {'status': 'closed'}, format='json')
                self.assertEqual(response.status_code, expected)

    def test_all_firm_roles_can_read_and_update_status(self):
        item = self.consultation()
        for actor in [self.admin_user, self.staff, self.lawyer]:
            self.api.force_authenticate(actor)
            self.assertEqual(self.api.get('/api/consultations/').status_code, 200)
            response = self.api.patch(f'/api/consultations/{item.pk}/', {'status': 'contacted'}, format='json')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['handled_by'], actor.pk)

    def test_staff_update_cannot_change_submitted_content_or_force_conversion(self):
        item = self.consultation()
        self.api.force_authenticate(self.staff)
        response = self.api.patch(f'/api/consultations/{item.pk}/', {'name': 'Forged', 'client': self.two.pk, 'status': 'contacted'}, format='json')
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.name, 'Sample Visitor')
        self.assertIsNone(item.client)
        self.assertEqual(self.api.patch(f'/api/consultations/{item.pk}/', {'status': 'converted'}, format='json').status_code, 400)

    def test_conversion_is_idempotent_and_preserves_contact(self):
        item = self.consultation()
        self.api.force_authenticate(self.staff)
        count = Client.objects.count()
        first = self.api.post(f'/api/consultations/{item.pk}/convert/', {}, format='json')
        second = self.api.post(f'/api/consultations/{item.pk}/convert/', {}, format='json')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data['client_id'], second.data['client_id'])
        self.assertFalse(second.data['created'])
        self.assertEqual(Client.objects.count(), count + 1)
        client = Client.objects.get(pk=first.data['client_id'])
        self.assertEqual(client.full_name, item.name)
        self.assertEqual(client.phone, item.phone)
        self.assertEqual(client.email, item.email)
        self.assertEqual(client.created_by, self.staff)
        self.assertIsNone(client.user)
        item.refresh_from_db()
        self.assertEqual(item.handled_by, self.staff)
        self.assertEqual(item.status, 'converted')
        self.assertEqual(Appointment.objects.count(), 0)

    def test_closed_request_must_be_reopened_before_conversion(self):
        item = self.consultation(status='closed')
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.api.post(f'/api/consultations/{item.pk}/convert/', {}, format='json').status_code, 400)
        self.assertEqual(self.api.patch(f'/api/consultations/{item.pk}/', {'status': 'contacted'}, format='json').status_code, 200)
        self.assertEqual(self.api.post(f'/api/consultations/{item.pk}/convert/', {}, format='json').status_code, 201)

    def test_converted_request_cannot_be_reopened(self):
        item, _ = convert_consultation(self.consultation().pk, self.staff)
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.api.patch(f'/api/consultations/{item.pk}/', {'status': 'new'}, format='json').status_code, 400)
        item.status = 'closed'
        item.client = None
        with self.assertRaises(ValidationError):
            item.save()

    def test_failed_conversion_rolls_back_client_creation(self):
        item = self.consultation()
        before = Client.objects.count()
        with patch.object(ConsultationRequest, 'save', side_effect=ValidationError('Simulated failure')):
            with self.assertRaises(ValidationError):
                convert_consultation(item.pk, self.staff)
        self.assertEqual(Client.objects.count(), before)
        item.refresh_from_db()
        self.assertEqual(item.status, 'new')
        self.assertIsNone(item.client)

    def test_stale_status_edit_does_not_undo_a_conversion(self):
        item = self.consultation()
        stale = ConsultationRequest.objects.get(pk=item.pk)
        convert_consultation(item.pk, self.staff)
        stale.status = 'closed'
        with self.assertRaises(ValidationError):
            stale.save()

    def test_consultations_are_not_hard_deleted(self):
        item = self.consultation()
        self.api.force_authenticate(self.admin_user)
        self.assertEqual(self.api.delete(f'/api/consultations/{item.pk}/').status_code, 405)


class AppointmentAPITests(IntakeFixtures):
    def test_firm_roles_can_create_read_update_and_delete(self):
        for actor in [self.admin_user, self.staff, self.lawyer]:
            self.api.force_authenticate(actor)
            response = self.api.post('/api/appointments/', self.appointment_payload(), format='json')
            self.assertEqual(response.status_code, 201, response.data)
            url = f"/api/appointments/{response.data['id']}/"
            self.assertEqual(self.api.get(url).status_code, 200)
            self.assertEqual(self.api.patch(url, {'notes': 'Updated'}, format='json').status_code, 200)
            self.assertEqual(self.api.delete(url).status_code, 204)

    def test_creator_cannot_be_forged_or_changed(self):
        self.api.force_authenticate(self.staff)
        response = self.api.post('/api/appointments/', self.appointment_payload(created_by=self.admin_user.pk), format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['created_by'], self.staff.pk)
        response = self.api.patch(f"/api/appointments/{response.data['id']}/", {'created_by': self.admin_user.pk}, format='json')
        self.assertEqual(response.data['created_by'], self.staff.pk)

    def test_anonymous_appointment_access_is_denied(self):
        item = self.appointment()
        self.assertEqual(self.api.get('/api/appointments/').status_code, 401)
        self.assertEqual(self.api.get(f'/api/appointments/{item.pk}/').status_code, 401)
        self.assertEqual(self.api.post('/api/appointments/', self.appointment_payload(), format='json').status_code, 401)

    def test_client_sees_only_own_appointments_without_internal_fields(self):
        own = self.appointment()
        other = self.appointment(client=self.two, lawyer=self.other_lawyer)
        self.api.force_authenticate(self.one_user)
        response = self.api.get('/api/appointments/')
        self.assertEqual(response.data['count'], 1)
        data = response.data['results'][0]
        self.assertEqual(data['id'], own.pk)
        self.assertEqual(set(data), {'id', 'case', 'lawyer_name', 'start', 'end', 'appointment_type', 'status'})
        self.assertIsNone(data['case'])
        self.assertEqual(data['lawyer_name'], 'Demo Lawyer')
        self.assertEqual(self.api.get(f'/api/appointments/{other.pk}/').status_code, 404)
        self.assertEqual(self.api.get(f'/api/appointments/?client={self.two.pk}').data['count'], 1)

    def test_client_cannot_book_change_or_delete(self):
        item = self.appointment()
        self.api.force_authenticate(self.one_user)
        self.assertEqual(self.api.post('/api/appointments/', self.appointment_payload(), format='json').status_code, 403)
        for method in ['put', 'patch', 'delete']:
            self.assertEqual(getattr(self.api, method)(f'/api/appointments/{item.pk}/', {}, format='json').status_code, 403)

    def test_unlinked_client_has_empty_appointment_list(self):
        user = User.objects.create_user(username='unlinked', role='client')
        self.appointment()
        self.api.force_authenticate(user)
        self.assertEqual(self.api.get('/api/appointments/').data['count'], 0)

    def test_invalid_duration_is_rejected(self):
        self.api.force_authenticate(self.staff)
        for end in [self.start, self.start - timedelta(minutes=1)]:
            response = self.api.post('/api/appointments/', self.appointment_payload(end=end.isoformat()), format='json')
            self.assertEqual(response.status_code, 400)
        self.assertEqual(Appointment.objects.count(), 0)

    def test_overlaps_including_containment_are_rejected(self):
        self.appointment()
        self.api.force_authenticate(self.staff)
        for start, end in [
            (self.start, self.end),
            (self.start - timedelta(minutes=30), self.end + timedelta(minutes=30)),
            (self.start + timedelta(minutes=10), self.end - timedelta(minutes=10)),
            (self.start - timedelta(minutes=10), self.start + timedelta(minutes=10)),
            (self.end - timedelta(minutes=10), self.end + timedelta(minutes=10)),
        ]:
            response = self.api.post('/api/appointments/', self.appointment_payload(start=start.isoformat(), end=end.isoformat()), format='json')
            self.assertEqual(response.status_code, 400, response.data)

    def test_adjacent_slots_and_other_lawyers_are_allowed(self):
        self.appointment()
        self.api.force_authenticate(self.staff)
        for data in [
            self.appointment_payload(start=self.end.isoformat(), end=(self.end + timedelta(hours=1)).isoformat()),
            self.appointment_payload(start=(self.start - timedelta(hours=1)).isoformat(), end=self.start.isoformat()),
            self.appointment_payload(lawyer=self.other_lawyer.pk),
        ]:
            self.assertEqual(self.api.post('/api/appointments/', data, format='json').status_code, 201)

    def test_cancelled_and_completed_appointments_do_not_block_booking(self):
        self.appointment(status='cancelled')
        self.appointment(status='completed')
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.api.post('/api/appointments/', self.appointment_payload(), format='json').status_code, 201)

    def test_rescheduling_is_validated_and_failed_update_does_not_persist(self):
        first = self.appointment()
        later = self.appointment(start=self.end, end=self.end + timedelta(hours=1))
        self.api.force_authenticate(self.staff)
        response = self.api.patch(f'/api/appointments/{later.pk}/', {'start': self.start.isoformat()}, format='json')
        self.assertEqual(response.status_code, 400)
        later.refresh_from_db()
        self.assertEqual(later.start, self.end)
        self.assertEqual(self.api.patch(f'/api/appointments/{first.pk}/', {'notes': 'Only notes'}, format='json').status_code, 200)

    def test_reassigning_lawyer_checks_new_lawyer_schedule(self):
        self.appointment()
        other = self.appointment(lawyer=self.other_lawyer)
        self.api.force_authenticate(self.staff)
        response = self.api.patch(f'/api/appointments/{other.pk}/', {'lawyer': self.lawyer.pk}, format='json')
        self.assertEqual(response.status_code, 400)
        other.refresh_from_db()
        self.assertEqual(other.lawyer_id, self.other_lawyer.pk)

    def test_reopening_cancelled_booking_rechecks_conflicts(self):
        cancelled = self.appointment(status='cancelled')
        self.appointment()
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.api.patch(f'/api/appointments/{cancelled.pk}/', {'status': 'scheduled'}, format='json').status_code, 400)

    def test_invalid_lawyer_and_inactive_client_rejected(self):
        self.api.force_authenticate(self.staff)
        for lawyer in [self.staff, self.one_user]:
            self.assertEqual(self.api.post('/api/appointments/', self.appointment_payload(lawyer=lawyer.pk), format='json').status_code, 400)
        self.lawyer.is_active = False
        self.lawyer.save(update_fields=['is_active'])
        self.assertEqual(self.api.post('/api/appointments/', self.appointment_payload(), format='json').status_code, 400)
        self.one.status = 'archived'
        self.one.save()
        self.assertEqual(self.api.post('/api/appointments/', self.appointment_payload(lawyer=self.other_lawyer.pk), format='json').status_code, 400)

    def test_existing_appointment_can_be_cancelled_after_lawyer_deactivation(self):
        item = self.appointment()
        self.lawyer.is_active = False
        self.lawyer.save(update_fields=['is_active'])
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.api.patch(f'/api/appointments/{item.pk}/', {'status': 'cancelled'}, format='json').status_code, 200)

    def test_timezone_equivalent_dates_still_conflict(self):
        self.appointment()
        local_start = timezone.localtime(self.start)
        local_end = timezone.localtime(self.end)
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.api.post('/api/appointments/', self.appointment_payload(start=local_start.isoformat(), end=local_end.isoformat()), format='json').status_code, 400)

    def test_database_rejects_nonpositive_duration_if_save_is_bypassed(self):
        item = self.appointment()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Appointment.objects.filter(pk=item.pk).update(end=item.start)


class IntakeAdminTests(IntakeFixtures):
    def test_admin_pages_render_and_client_role_cannot_enter(self):
        self.client.force_login(self.admin_user)
        for url in ['/admin/intake/consultationrequest/', '/admin/intake/appointment/', '/admin/intake/appointment/add/']:
            self.assertEqual(self.client.get(url).status_code, 200)
        self.one_user.is_staff = True
        self.one_user.save(update_fields=['is_staff'])
        self.one_user.user_permissions.set(Permission.objects.filter(content_type__app_label='intake'))
        self.client.force_login(self.one_user)
        for url in ['/admin/intake/consultationrequest/', '/admin/intake/appointment/', '/admin/intake/appointment/add/']:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_admin_action_converts_and_handles_closed_requests(self):
        item = self.consultation()
        closed = self.consultation(status='closed')
        self.client.force_login(self.admin_user)
        response = self.client.post('/admin/intake/consultationrequest/', {
            'action': 'convert_selected', '_selected_action': [item.pk, closed.pk],
        })
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        closed.refresh_from_db()
        self.assertEqual(item.status, 'converted')
        self.assertEqual(closed.status, 'closed')

    def test_admin_form_displays_booking_conflict(self):
        self.appointment()
        self.client.force_login(self.admin_user)
        start = timezone.localtime(self.start)
        end = timezone.localtime(self.end)
        response = self.client.post('/admin/intake/appointment/add/', {
            'client': self.one.pk, 'lawyer': self.lawyer.pk,
            'start_0': start.strftime('%Y-%m-%d'), 'start_1': start.strftime('%H:%M:%S'),
            'end_0': end.strftime('%Y-%m-%d'), 'end_1': end.strftime('%H:%M:%S'),
            'appointment_type': 'consultation', 'status': 'scheduled', 'notes': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'overlapping appointment')
        self.assertEqual(Appointment.objects.count(), 1)

    def test_conflict_detected_during_admin_save_does_not_return_500(self):
        self.client.force_login(self.admin_user)
        start = timezone.localtime(self.start)
        end = timezone.localtime(self.end)
        with patch.object(Appointment, 'save', side_effect=ValidationError('Concurrent booking conflict')):
            response = self.client.post('/admin/intake/appointment/add/', {
                'client': self.one.pk, 'lawyer': self.lawyer.pk,
                'start_0': start.strftime('%Y-%m-%d'), 'start_1': start.strftime('%H:%M:%S'),
                'end_0': end.strftime('%Y-%m-%d'), 'end_1': end.strftime('%H:%M:%S'),
                'appointment_type': 'consultation', 'status': 'scheduled', 'notes': '',
            }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Concurrent booking conflict')
        self.assertEqual(Appointment.objects.count(), 0)


@skipUnlessDBFeature('has_select_for_update')
class IntakeConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.actor = User.objects.create_user(username='actor', role='admin')
        self.lawyer = User.objects.create_user(username='lawyer', role='lawyer')
        self.client_record = Client.objects.create(full_name='Concurrent', created_by=self.actor)
        self.start = timezone.now() + timedelta(days=3)
        self.end = self.start + timedelta(hours=1)

    def test_simultaneous_bookings_accept_only_one(self):
        barrier = Barrier(2)
        def book():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    Appointment.objects.create(
                        client_id=self.client_record.pk, lawyer_id=self.lawyer.pk,
                        created_by_id=self.actor.pk, start=self.start, end=self.end,
                    )
                    return 'created'
                except ValidationError:
                    return 'conflict'
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(book) for _ in range(2)]
            results = [future.result(timeout=20) for future in futures]
        self.assertCountEqual(results, ['created', 'conflict'])
        self.assertEqual(Appointment.objects.count(), 1)

    def test_simultaneous_conversions_create_only_one_client(self):
        area = PracticeArea.objects.create(name='Civil', slug='civil')
        item = ConsultationRequest.objects.create(name='Concurrent Visitor', phone='123', practice_area=area, message='Sample')
        count = Client.objects.count()
        barrier = Barrier(2)
        def convert():
            close_old_connections()
            try:
                actor = User.objects.get(pk=self.actor.pk)
                barrier.wait(timeout=10)
                result, created = convert_consultation(item.pk, actor)
                return result.client_id, created
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(convert) for _ in range(2)]
            results = [future.result(timeout=20) for future in futures]
        self.assertEqual(results[0][0], results[1][0])
        self.assertCountEqual([created for _, created in results], [True, False])
        self.assertEqual(Client.objects.count(), count + 1)
