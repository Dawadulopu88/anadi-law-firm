from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from cases.tests import CaseFixtures
from clients.models import Client
from .models import Invoice, Payment


class BillingTests(CaseFixtures):
    def setUp(self):
        super().setUp()
        self.invoice = Invoice.objects.create(invoice_number='TEST-1', client=self.one, case=self.case, issue_date=timezone.localdate(), due_date=timezone.localdate(), amount=Decimal('100.00'), created_by=self.staff)
        self.login(self.staff)

    def pay(self, amount='40.00', **kwargs):
        data = dict(invoice=self.invoice.pk, amount=amount, method='cash', date=str(timezone.localdate()))
        data.update(kwargs)
        return self.api.post('/api/payments/', data, format='json')

    def test_status_and_balance_calculated(self):
        path = f'/api/invoices/{self.invoice.pk}/'
        self.assertEqual(self.api.get(path).data['status'], 'unpaid')
        self.assertEqual(self.pay().status_code, 201)
        self.assertEqual(self.api.get(path).data['balance'], '60.00')
        self.assertEqual(self.api.get(path).data['status'], 'partial')
        self.assertEqual(self.pay('60.00').status_code, 201)
        self.assertEqual(self.api.get(path).data['status'], 'paid')
        self.assertEqual(self.pay('0.01').status_code, 400)

    def test_money_validation_and_actor(self):
        for amount in ('0.00', '-1.00', '100.01', '1.001', 'NaN'):
            self.assertEqual(self.pay(amount).status_code, 400)
        response = self.pay(recorded_by=self.owner.pk)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['recorded_by'], self.staff.pk)

    def test_invoice_client_consistency_and_immutable_owner(self):
        path = f'/api/invoices/{self.invoice.pk}/'
        self.assertEqual(self.api.patch(path, {'case': self.other_case.pk}, format='json').status_code, 400)
        self.assertEqual(self.api.patch(path, {'client': self.two.pk, 'case': self.other_case.pk}, format='json').status_code, 400)

    def test_amount_cannot_drop_below_payments(self):
        self.pay('60.00')
        response = self.api.patch(f'/api/invoices/{self.invoice.pk}/', {'amount': '50.00'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount, Decimal('100.00'))

    def test_payment_edit_delete_recalculates_balance(self):
        first = self.pay('40.00').data['id']
        self.pay('50.00')
        path = f'/api/payments/{first}/'
        self.assertEqual(self.api.patch(path, {'amount': '60.00'}, format='json').status_code, 400)
        self.assertEqual(self.api.patch(path, {'amount': '30.00'}, format='json').status_code, 200)
        self.assertEqual(self.invoice.balance, Decimal('20.00'))
        self.assertEqual(self.api.delete(path).status_code, 204)
        self.assertEqual(self.invoice.balance, Decimal('50.00'))

    def test_invoice_with_payments_cannot_delete(self):
        self.pay()
        self.assertEqual(self.api.delete(f'/api/invoices/{self.invoice.pk}/').status_code, 400)

    def test_client_only_own_invoice_no_payment_access(self):
        self.login(self.owner)
        data = self.results('/api/invoices/')[0]
        self.assertNotIn('created_by', data)
        self.assertEqual(self.api.get('/api/payments/').status_code, 403)
        self.assertEqual(self.api.patch(f'/api/invoices/{self.invoice.pk}/', {'amount': '1.00'}, format='json').status_code, 403)
        self.login(self.outsider)
        self.assertEqual(self.results('/api/invoices/'), [])
        self.assertEqual(self.api.get(f'/api/invoices/{self.invoice.pk}/').status_code, 404)

    def test_invoice_create_and_admin(self):
        data = dict(invoice_number='TEST-2', client=self.one.pk, amount='20.00', issue_date=str(timezone.localdate()), due_date=str(timezone.localdate()))
        self.assertEqual(self.api.post('/api/invoices/', data, format='json').status_code, 201)
        self.assertEqual(self.api.post('/api/invoices/', data, format='json').status_code, 400)
        self.client.force_login(self.admin_user)
        for model in ('invoice', 'payment'):
            self.assertEqual(self.client.get(f'/admin/billing/{model}/add/').status_code, 200)


@skipUnlessDBFeature('has_select_for_update')
class ConcurrentPaymentTests(TransactionTestCase):
    def test_parallel_payments_cannot_exceed_invoice(self):
        user = get_user_model().objects.create_user(username='cashier', role='staff')
        client = Client.objects.create(full_name='Sample', created_by=user)
        invoice = Invoice.objects.create(invoice_number='PARALLEL', client=client, amount=Decimal('100.00'), issue_date=timezone.localdate(), due_date=timezone.localdate(), created_by=user)
        barrier = Barrier(2)
        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                Payment.objects.create(invoice_id=invoice.pk, amount=Decimal('60.00'), method='cash', date=timezone.localdate(), recorded_by_id=user.pk)
                return True
            except ValidationError:
                return False
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: worker(), range(2)))
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(invoice.paid_amount, Decimal('60.00'))
