from django.contrib import admin
from intake.admin import FirmMemberAdmin
from .models import Invoice, Payment


@admin.register(Invoice)
class InvoiceAdmin(FirmMemberAdmin):
    list_display = ('invoice_number', 'client', 'amount', 'paid_amount', 'balance', 'status')
    search_fields = ('invoice_number', 'client__full_name')
    list_select_related = ('client',)
    list_filter = ('issue_date',)
    readonly_fields = ('created_by', 'created_at', 'updated_at', 'paid_amount', 'balance', 'status')
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    def delete_queryset(self, request, queryset):
        for obj in queryset.order_by('pk'):
            obj.delete()


@admin.register(Payment)
class PaymentAdmin(FirmMemberAdmin):
    list_display = ('invoice', 'amount', 'method', 'date')
    search_fields = ('invoice__invoice_number', 'reference')
    list_select_related = ('invoice',)
    list_filter = ('method', 'date')
    readonly_fields = ('recorded_by', 'created_at', 'updated_at')
    def save_model(self, request, obj, form, change):
        if not change:
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)
    def delete_queryset(self, request, queryset):
        for obj in queryset.order_by('invoice_id', 'pk'):
            obj.delete()
