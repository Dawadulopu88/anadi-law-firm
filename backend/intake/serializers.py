from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as ModelValidationError
from django.utils import timezone
from rest_framework import serializers

from clients.models import Client
from firm.models import PracticeArea
from .models import Appointment, ConsultationRequest


def api_validation_error(error):
    detail = error.message_dict if hasattr(error, 'message_dict') else {'non_field_errors': error.messages}
    if '__all__' in detail:
        detail['non_field_errors'] = detail.pop('__all__')
    return serializers.ValidationError(detail)


class PublicConsultationSerializer(serializers.ModelSerializer):
    practice_area = serializers.PrimaryKeyRelatedField(queryset=PracticeArea.objects.filter(is_active=True))
    website = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=200)

    class Meta:
        model = ConsultationRequest
        fields = ('name', 'phone', 'email', 'practice_area', 'message', 'preferred_date', 'preferred_language', 'website')

    def validate_website(self, value):
        if value.strip():
            raise serializers.ValidationError('Unable to accept this submission.')
        return value

    def validate_preferred_date(self, value):
        if value and value < timezone.localdate():
            raise serializers.ValidationError('Preferred date cannot be in the past.')
        return value

    def create(self, validated_data):
        validated_data.pop('website', None)
        try:
            return super().create(validated_data)
        except ModelValidationError as error:
            raise api_validation_error(error)


class StaffConsultationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultationRequest
        fields = (
            'id', 'name', 'phone', 'email', 'practice_area', 'message', 'preferred_date',
            'preferred_language', 'status', 'handled_by', 'client', 'created_at', 'updated_at',
        )
        read_only_fields = tuple(field for field in fields if field != 'status')

    def validate_status(self, value):
        if value == ConsultationRequest.Status.CONVERTED and self.instance.status != value:
            raise serializers.ValidationError('Use the convert action to create and link a client.')
        if self.instance.status == ConsultationRequest.Status.CONVERTED and value != self.instance.status:
            raise serializers.ValidationError('A converted request cannot be reopened.')
        return value

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except ModelValidationError as error:
            raise api_validation_error(error)


class StaffAppointmentSerializer(serializers.ModelSerializer):
    lawyer = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.filter(role='lawyer', is_active=True))
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from cases.models import Case
        from cases.permissions import visible_cases
        request = self.context.get('request')
        self.fields['case'].queryset = visible_cases(request.user) if request else Case.objects.none()

    class Meta:
        model = Appointment
        fields = (
            'id', 'client', 'case', 'lawyer', 'start', 'end', 'appointment_type', 'status',
            'notes', 'created_by', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except ModelValidationError as error:
            raise api_validation_error(error)

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except ModelValidationError as error:
            raise api_validation_error(error)


class OwnAppointmentSerializer(serializers.ModelSerializer):
    lawyer_name = serializers.CharField(source='lawyer.get_full_name', read_only=True)

    class Meta:
        model = Appointment
        fields = ('id', 'case', 'lawyer_name', 'start', 'end', 'appointment_type', 'status')
        read_only_fields = fields
