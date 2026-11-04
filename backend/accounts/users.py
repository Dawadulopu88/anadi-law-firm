"""Firm account directory and admin-only account administration API.

Firm members (admin/staff/lawyer) can list active firm users and client logins so
the frontend can pick lawyers, assignees and portal logins. Only the application
admin role may create or edit accounts. There is still no public signup.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import has_role, is_firm_member

User = get_user_model()


class DirectoryPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return is_firm_member(request.user)
        return has_role(request.user, 'admin')


class UserDirectorySerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    has_client_record = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'full_name', 'first_name', 'last_name', 'role', 'is_active', 'has_client_record')
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_has_client_record(self, obj):
        return hasattr(obj, 'client_profile') if obj.role == 'client' else None


class UserAdminSerializer(UserDirectorySerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=False, min_length=8, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('id', 'username', 'full_name', 'first_name', 'last_name', 'email', 'phone',
                  'role', 'is_active', 'has_client_record', 'password', 'date_joined', 'last_login')
        read_only_fields = ('id', 'full_name', 'has_client_record', 'date_joined', 'last_login')

    def validate(self, attrs):
        request = self.context['request']
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({'password': 'Set an initial password for the new account.'})
        if self.instance is not None:
            if self.instance.pk == request.user.pk and (
                attrs.get('is_active') is False or attrs.get('role', self.instance.role) != self.instance.role
            ):
                raise serializers.ValidationError('You cannot deactivate or change the role of your own account.')
            if self.instance.is_superuser and attrs.get('role', 'admin') != 'admin':
                raise serializers.ValidationError({'role': 'A superuser must keep the admin role.'})
        password = attrs.get('password')
        if password:
            candidate = User(**{k: v for k, v in attrs.items() if k in ('username', 'first_name', 'last_name', 'email')})
            if self.instance is not None:
                candidate = self.instance
            try:
                validate_password(password, candidate)
            except DjangoValidationError as error:
                raise serializers.ValidationError({'password': list(error.messages)})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                  mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [DirectoryPermission]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        queryset = User.objects.all().order_by('role', 'first_name', 'username')
        if not has_role(self.request.user, 'admin'):
            queryset = queryset.filter(is_active=True)
        params = self.request.query_params
        role = params.get('role')
        if role:
            roles = [item for item in role.split(',') if item in User.Role.values]
            if not roles:
                raise serializers.ValidationError({'role': 'Unknown role.'})
            queryset = queryset.filter(role__in=roles)
        search = params.get('search', '').strip()
        if search:
            queryset = queryset.filter(Q(username__icontains=search) | Q(first_name__icontains=search)
                                       | Q(last_name__icontains=search) | Q(email__icontains=search))
        if params.get('without_client') in ('1', 'true'):
            queryset = queryset.filter(role='client', client_profile__isnull=True)
        return queryset.select_related('client_profile')

    def get_serializer_class(self):
        return UserAdminSerializer if has_role(self.request.user, 'admin') else UserDirectorySerializer


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({'current_password': 'Current password is incorrect.'})
        try:
            validate_password(attrs['new_password'], user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({'new_password': list(error.messages)})
        return attrs


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ['post', 'head', 'options']

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        return Response({'detail': 'Password changed.'}, status=status.HTTP_200_OK)
