from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Client


class StaffClientSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.filter(role='client', is_active=True),
        required=False, allow_null=True,
    )

    assigned_lawyer = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.filter(role='lawyer'), required=False, allow_null=True,
    )
    assigned_lawyer_name = serializers.SerializerMethodField()

    def get_assigned_lawyer_name(self, obj):
        lawyer = obj.assigned_lawyer
        return (lawyer.get_full_name() or lawyer.username) if lawyer else None

    def validate_assigned_lawyer(self, lawyer):
        unchanged = self.instance is not None and self.instance.assigned_lawyer_id == getattr(lawyer, 'pk', None)
        if lawyer is not None and not unchanged and not lawyer.is_active:
            raise serializers.ValidationError('Choose an active lawyer.')
        return lawyer

    class Meta:
        model = Client
        fields = (
            'id', 'user', 'assigned_lawyer', 'assigned_lawyer_name', 'full_name', 'phone', 'email', 'address',
            'nid_or_reference', 'status', 'notes', 'created_by', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'assigned_lawyer_name', 'created_by', 'created_at', 'updated_at')

    def validate_user(self, user):
        if user is not None:
            matches = Client.objects.filter(user=user)
            if self.instance:
                matches = matches.exclude(pk=self.instance.pk)
            if matches.exists():
                raise serializers.ValidationError('This user is already linked to a client.')
        return user


class OwnClientSerializer(serializers.ModelSerializer):
    """Deliberately omit staff notes, identity references and staff-account IDs."""
    assigned_lawyer_name = serializers.SerializerMethodField()

    def get_assigned_lawyer_name(self, obj):
        lawyer = obj.assigned_lawyer
        return (lawyer.get_full_name() or lawyer.username) if lawyer else None

    class Meta:
        model = Client
        fields = ('id', 'full_name', 'phone', 'email', 'address', 'status', 'assigned_lawyer_name', 'created_at', 'updated_at')
        read_only_fields = fields
