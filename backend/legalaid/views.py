from django.core.exceptions import ValidationError as ModelValidationError
from django.shortcuts import get_object_or_404
from rest_framework import generics, mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from accounts.permissions import IsFirmMember
from accounts.throttles import PublicFormBurst, PublicFormDaily, PublicTracking
from cases.serializers import ValidatedSerializer
from firm.models import PracticeArea
from intake.serializers import api_validation_error
from .models import LegalAidApplication, validate_answers
from .services import convert_application


class ApplicationSerializer(ValidatedSerializer):
    practice_area = serializers.PrimaryKeyRelatedField(queryset=PracticeArea.objects.filter(is_active=True))
    website = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=200)
    class Meta:
        model = LegalAidApplication
        fields = ('applicant_name', 'phone', 'email', 'practice_area', 'description', 'income_range', 'eligibility_answers', 'website')
    def validate_website(self, value):
        if value.strip():
            raise serializers.ValidationError('Unable to accept this submission.')
        return value
    def validate_eligibility_answers(self, value):
        try:
            validate_answers(value)
        except ModelValidationError as error:
            raise api_validation_error(error)
        return value
    def create(self, validated_data):
        validated_data.pop('website', None)
        return super().create(validated_data)


class ApplyView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [PublicFormBurst, PublicFormDaily]
    serializer_class = ApplicationSerializer
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        return Response({'tracking_code': application.tracking_code, 'status': application.status}, status=201)


class TrackView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [PublicTracking]
    def get(self, request, code):
        application = get_object_or_404(LegalAidApplication, tracking_code=code)
        response = Response({'status': application.status})
        response['Cache-Control'] = 'no-store'
        response['Referrer-Policy'] = 'no-referrer'
        return response


class StaffApplicationSerializer(ValidatedSerializer):
    class Meta:
        model = LegalAidApplication
        fields = ('id', 'tracking_code', 'applicant_name', 'phone', 'email', 'practice_area', 'description', 'income_range', 'eligibility_answers', 'status', 'reviewed_by', 'client', 'case', 'created_at', 'updated_at')
        read_only_fields = tuple(f for f in fields if f != 'status')


class ApplicationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsFirmMember]
    serializer_class = StaffApplicationSerializer

    def get_queryset(self):
        queryset = LegalAidApplication.objects.all()
        value = self.request.query_params.get('status') if self.action == 'list' else None
        if value:
            if value not in ('submitted', 'under_review', 'matched', 'declined'):
                raise serializers.ValidationError({'status': 'Unknown application status.'})
            queryset = queryset.filter(status=value)
        return queryset

    def perform_update(self, serializer):
        serializer.save(reviewed_by=self.request.user)
    @action(detail=True, methods=['post'])
    def convert(self, request, pk=None):
        self.get_object()
        try:
            application, created = convert_application(pk, request.user)
        except ModelValidationError as error:
            raise api_validation_error(error)
        return Response({'client': application.client_id, 'case': application.case_id, 'status': application.status, 'created': created}, status=201 if created else 200)
