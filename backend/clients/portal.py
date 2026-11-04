from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from accounts.permissions import IsClient
from cases.models import Case, Hearing
from cases.serializers import OwnCaseSerializer
from cases.work import OwnHearingSerializer
from intake.models import Appointment
from intake.serializers import OwnAppointmentSerializer
from documents.views import visible_documents, OwnDocumentSerializer
from billing.models import Invoice, Payment
from billing.views import OwnInvoiceSerializer


class PortalViewSet(viewsets.GenericViewSet):
    permission_classes = [IsClient]
    http_method_names = ['get', 'head', 'options']

    def page(self, queryset, serializer):
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(serializer(page, many=True, context={'request': self.request}).data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        user = request.user
        cases = Case.objects.filter(client__user=user)
        invoices = Invoice.objects.filter(client__user=user)
        amount = invoices.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        paid = Payment.objects.filter(invoice__client__user=user).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        return Response({'cases': cases.count(), 'active_cases': cases.exclude(status__in=['closed', 'archived']).count(),
                         'upcoming_hearings': Hearing.objects.filter(case__client__user=user, hearing_at__gte=timezone.now()).count(),
                         'upcoming_appointments': Appointment.objects.filter(client__user=user, start__gte=timezone.now(), status='scheduled').count(),
                         'documents': visible_documents(user).count(), 'invoices': invoices.count(),
                         'outstanding_balance': format(amount - paid, '.2f'), 'currency': 'BDT'})

    @action(detail=False, methods=['get'])
    def cases(self, request):
        return self.page(Case.objects.filter(client__user=request.user), OwnCaseSerializer)

    @action(detail=False, methods=['get'])
    def hearings(self, request):
        return self.page(Hearing.objects.filter(case__client__user=request.user, hearing_at__gte=timezone.now()), OwnHearingSerializer)

    @action(detail=False, methods=['get'])
    def appointments(self, request):
        return self.page(Appointment.objects.filter(client__user=request.user).select_related('lawyer'), OwnAppointmentSerializer)

    @action(detail=False, methods=['get'])
    def documents(self, request):
        return self.page(visible_documents(request.user), OwnDocumentSerializer)

    @action(detail=False, methods=['get'])
    def invoices(self, request):
        return self.page(Invoice.objects.filter(client__user=request.user), OwnInvoiceSerializer)
