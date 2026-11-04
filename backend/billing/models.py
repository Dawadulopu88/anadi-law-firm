from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum
from cases.models import ValidatedModel


class Invoice(ValidatedModel):
    invoice_number = models.CharField(max_length=100, unique=True)
    client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='invoices')
    case = models.ForeignKey('cases.Case', on_delete=models.PROTECT, null=True, blank=True, related_name='invoices')
    issue_date = models.DateField()
    due_date = models.DateField()
    description = models.CharField(max_length=500, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, editable=False, related_name='created_invoices')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-issue_date', '-pk']
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name='billing_invoice_positive_amount'),
                       models.CheckConstraint(condition=models.Q(due_date__gte=models.F('issue_date')), name='billing_invoice_valid_dates')]

    @property
    def paid_amount(self):
        if not self.pk:
            return Decimal('0.00')
        return self.payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    @property
    def balance(self):
        return (self.amount or Decimal('0.00')) - self.paid_amount

    @property
    def status(self):
        if self.amount is None:
            return 'unpaid'
        paid = self.paid_amount
        return 'paid' if paid >= self.amount else ('partial' if paid else 'unpaid')

    def clean(self):
        super().clean()
        errors = {}
        if self.case_id and self.client_id and self.case.client_id != self.client_id:
            errors['case'] = 'The invoice case must belong to its client.'
        if self.amount is not None and (self.amount <= 0 or self.amount < self.paid_amount):
            errors['amount'] = 'Amount must be positive and cannot be below recorded payments.'
        if self.issue_date and self.due_date and self.due_date < self.issue_date:
            errors['due_date'] = 'Due date cannot be before issue date.'
        if self.pk and type(self).objects.filter(pk=self.pk).exclude(client_id=self.client_id).exists():
            errors['client'] = 'Invoice ownership cannot be transferred.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.pk:
                type(self).objects.select_for_update().get(pk=self.pk)
            return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            type(self).objects.select_for_update().get(pk=self.pk)
            return super().delete(*args, **kwargs)

    def __str__(self):
        return self.invoice_number


class Payment(ValidatedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=15, choices=[('cash', 'Cash'), ('bank', 'Bank'), ('mobile_banking', 'Mobile banking')])
    date = models.DateField()
    reference = models.CharField(max_length=200, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, editable=False, related_name='recorded_payments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-pk']
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name='billing_payment_positive_amount')]

    def clean(self):
        super().clean()
        if self.pk and type(self).objects.filter(pk=self.pk).exclude(invoice_id=self.invoice_id).exists():
            raise ValidationError({'invoice': 'Payments cannot be moved to another invoice.'})
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({'amount': 'Payment must be positive.'})
        if self.invoice_id and self.amount is not None:
            other = type(self).objects.filter(invoice_id=self.invoice_id).exclude(pk=self.pk).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            if other + self.amount > self.invoice.amount:
                raise ValidationError({'amount': 'Payment exceeds the remaining invoice balance.'})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            # All payment changes and invoice amount changes lock the same parent.
            self.invoice = Invoice.objects.select_for_update().get(pk=self.invoice_id)
            return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            Invoice.objects.select_for_update().get(pk=self.invoice_id)
            return super().delete(*args, **kwargs)

    def __str__(self):
        return f'{self.invoice} — {self.amount}'
