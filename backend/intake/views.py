from django.core.exceptions import ValidationError as ModelValidationError
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny

from accounts.permissions import IsFirmMember, is_firm_member
from .models import Appointment, ConsultationRequest


def filter_id(queryset, params, field):
    from cases.views import filter_id as shared_filter_id
    return shared_filter_id(queryset, params, field)
from .permissions import CanAccessAppointment
from .serializers import (
    OwnAppointmentSerializer, PublicConsultationSerializer,
    StaffAppointmentSerializer, StaffConsultationSerializer, api_validation_error,
)
from .services import convert_consultation
from .throttles import ConsultationBurstThrottle, ConsultationDailyThrottle
from rest_framework.response import Response


class ConsultationViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin, viewsets.GenericViewSet,
):
    def get_queryset(self):
        queryset = ConsultationRequest.objects.all()
        value = self.request.query_params.get('status') if self.action == 'list' else None
        if value:
            if value not in ConsultationRequest.Status.values:
                raise serializers.ValidationError({'status': 'Unknown consultation status.'})
            queryset = queryset.filter(status=value)
        return queryset

    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_permissions(self):
        return [AllowAny()] if self.action == 'create' else [IsFirmMember()]

    def get_throttles(self):
        return [ConsultationBurstThrottle(), ConsultationDailyThrottle()] if self.action == 'create' else []

    def get_serializer_class(self):
        return PublicConsultationSerializer if self.action == 'create' else StaffConsultationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        consultation = serializer.save()
        return Response({'id': consultation.pk, 'status': consultation.status}, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        serializer.save(handled_by=self.request.user)

    @action(detail=True, methods=['post'])
    def convert(self, request, pk=None):
        consultation = self.get_object()
        try:
            consultation, created = convert_consultation(consultation.pk, request.user)
        except ModelValidationError as error:
            raise api_validation_error(error)
        return Response({
            'consultation_id': consultation.pk, 'client_id': consultation.client_id,
            'status': consultation.status, 'created': created,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class AppointmentViewSet(viewsets.ModelViewSet):
    permission_classes = [CanAccessAppointment]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        queryset = Appointment.objects.select_related('client', 'lawyer')
        if not is_firm_member(self.request.user):
            # Client reads stay ownership-scoped; filters are a firm dashboard feature.
            return queryset.filter(client__user=self.request.user)
        params = self.request.query_params
        for field in ('client', 'case', 'lawyer'):
            queryset = filter_id(queryset, params, field)
        if params.get('status'):
            if params['status'] not in Appointment.Status.values:
                raise serializers.ValidationError({'status': 'Unknown appointment status.'})
            queryset = queryset.filter(status=params['status'])
        return queryset

    def get_serializer_class(self):
        return StaffAppointmentSerializer if is_firm_member(self.request.user) else OwnAppointmentSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
