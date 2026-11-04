from django.db.models.deletion import ProtectedError
from rest_framework import serializers, viewsets
from accounts.permissions import IsFirmMember, has_role, is_firm_member
from cases.permissions import CanAccessNotes
from cases.serializers import ValidatedSerializer
from cases.views import filter_id
from .models import Invoice, Payment


class InvoiceSerializer(ValidatedSerializer):
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    status = serializers.CharField(read_only=True)
    currency = serializers.SerializerMethodField()
    def get_currency(self, obj):
        return 'BDT'
    class Meta:
        model = Invoice
        fields = ('id', 'invoice_number', 'client', 'case', 'issue_date', 'due_date', 'description', 'amount', 'currency', 'paid_amount', 'balance', 'status', 'created_by', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')


class OwnInvoiceSerializer(InvoiceSerializer):
    class Meta(InvoiceSerializer.Meta):
        fields = tuple(f for f in InvoiceSerializer.Meta.fields if f not in ('client', 'created_by'))
        read_only_fields = fields


def visible_invoices(user):
    if is_firm_member(user):
        return Invoice.objects.all()
    if has_role(user, 'client'):
        return Invoice.objects.filter(client__user=user)
    return Invoice.objects.none()


class InvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = [CanAccessNotes]
    def get_queryset(self):
        queryset = filter_id(visible_invoices(self.request.user), self.request.query_params, 'client')
        return filter_id(queryset, self.request.query_params, 'case')
    def get_serializer_class(self):
        return OwnInvoiceSerializer if has_role(self.request.user, 'client') else InvoiceSerializer
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise serializers.ValidationError('An invoice with recorded payments cannot be deleted.')


class PaymentSerializer(ValidatedSerializer):
    class Meta:
        model = Payment
        fields = ('id', 'invoice', 'amount', 'method', 'date', 'reference', 'recorded_by', 'created_at', 'updated_at')
        read_only_fields = ('id', 'recorded_by', 'created_at', 'updated_at')


class PaymentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsFirmMember]
    serializer_class = PaymentSerializer
    def get_queryset(self):
        return filter_id(Payment.objects.all(), self.request.query_params, 'invoice')
    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)
