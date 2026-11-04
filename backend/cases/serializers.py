from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as ModelValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers

from intake.serializers import api_validation_error
from .models import Case, CaseAssignment, CaseNote
from .permissions import visible_cases


class ValidatedSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        try:
            with transaction.atomic():
                return super().create(validated_data)
        except ModelValidationError as error:
            raise api_validation_error(error)
        except IntegrityError:
            # Unique constraints also reject simultaneous duplicate submissions.
            raise serializers.ValidationError('A record with this unique reference already exists.')

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                return super().update(instance, validated_data)
        except ModelValidationError as error:
            raise api_validation_error(error)
        except IntegrityError:
            raise serializers.ValidationError('A record with this unique reference already exists.')


class CaseSerializer(ValidatedSerializer):
    lead_lawyers = serializers.SerializerMethodField()

    def get_lead_lawyers(self, obj):
        return [{'id': item.user_id, 'name': item.user.get_full_name() or item.user.username}
                for item in obj.assignments.filter(role='lead', user__role='lawyer', user__is_active=True).select_related('user')]

    class Meta:
        model = Case
        fields = ('id', 'case_number', 'title', 'description', 'client', 'practice_area', 'status', 'filing_date', 'court', 'opposite_party', 'priority', 'closed_date', 'lead_lawyers', 'created_by', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')


class OwnCaseSerializer(CaseSerializer):
    class Meta:
        model = Case
        fields = ('id', 'case_number', 'title', 'description', 'practice_area', 'status', 'filing_date', 'court', 'closed_date', 'lead_lawyers', 'created_at', 'updated_at')
        read_only_fields = fields


class AccessibleCaseSerializer(ValidatedSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        self.fields['case'].queryset = visible_cases(request.user) if request else Case.objects.none()


class CaseAssignmentSerializer(AccessibleCaseSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.filter(role__in=['lawyer', 'staff'], is_active=True), required=False)
    # Preserve earlier API clients. New integrations should send `user`.
    lawyer = serializers.PrimaryKeyRelatedField(source='user', queryset=get_user_model().objects.filter(role='lawyer', is_active=True), required=False)

    def validate(self, attrs):
        if 'user' in self.initial_data and 'lawyer' in self.initial_data:
            raise serializers.ValidationError('Send user or the legacy lawyer field, not both.')
        if 'user' not in attrs:
            raise serializers.ValidationError({'user': 'Choose a lawyer or staff member.'})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['lawyer'] = instance.user_id if instance.user.role == 'lawyer' else None
        return data

    class Meta:
        model = CaseAssignment
        fields = ('id', 'case', 'user', 'lawyer', 'role', 'assigned_by', 'assigned_at')
        read_only_fields = ('id', 'assigned_by', 'assigned_at')
        validators = []  # Model validation and the database enforce uniqueness.


class CaseNoteSerializer(AccessibleCaseSerializer):
    class Meta:
        model = CaseNote
        fields = ('id', 'case', 'body', 'is_internal', 'author', 'created_at')
        read_only_fields = ('id', 'author', 'created_at')


class OwnCaseNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseNote
        fields = ('id', 'case', 'body', 'created_at')
        read_only_fields = fields
