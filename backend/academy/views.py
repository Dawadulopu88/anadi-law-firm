from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, viewsets, serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from accounts.throttles import PublicFormBurst, PublicFormDaily
from cases.serializers import ValidatedSerializer
from cases.views import filter_id
from firm.serializers import LocalizedSerializer
from .models import Pathway, Course, LiveSession, SessionRegistration


def public_sessions():
    return LiveSession.objects.filter(is_published=True, start__gt=timezone.now()).filter(
        Q(course__isnull=True) | Q(course__is_published=True, course__pathway__is_active=True)
    ).select_related('course', 'course__pathway')


class PathwaySerializer(LocalizedSerializer):
    localized_fields = ('title', 'description')
    class Meta:
        model = Pathway
        fields = ('id', 'title', 'slug', 'description', 'is_sample')


class CourseSerializer(LocalizedSerializer):
    localized_fields = ('title', 'summary', 'duration')
    class Meta:
        model = Course
        fields = ('id', 'pathway', 'title', 'summary', 'level', 'duration', 'instructor', 'is_sample')


class SessionSerializer(LocalizedSerializer):
    localized_fields = ('title', 'venue')
    seats_remaining = serializers.IntegerField(read_only=True)
    class Meta:
        model = LiveSession
        fields = ('id', 'title', 'course', 'start', 'end', 'venue', 'meeting_link', 'capacity', 'seats_remaining', 'is_sample')


class PathwayViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = Pathway.objects.filter(is_active=True)
    serializer_class = PathwaySerializer
    lookup_field = 'slug'


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = CourseSerializer
    def get_queryset(self):
        return filter_id(Course.objects.filter(is_published=True, pathway__is_active=True), self.request.query_params, 'pathway')


class SessionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = SessionSerializer
    def get_queryset(self):
        return filter_id(public_sessions(), self.request.query_params, 'course')


class RegistrationSerializer(ValidatedSerializer):
    session = serializers.PrimaryKeyRelatedField(queryset=LiveSession.objects.none())
    website = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=200)
    class Meta:
        model = SessionRegistration
        fields = ('session', 'name', 'email', 'phone', 'website')
        # Normalization and duplicate checks are repeated under the session lock.
        validators = []
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['session'].queryset = public_sessions()
    def validate_website(self, value):
        if value.strip():
            raise serializers.ValidationError('Unable to accept this submission.')
        return value
    def create(self, validated_data):
        validated_data.pop('website', None)
        return super().create(validated_data)


class RegistrationView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [PublicFormBurst, PublicFormDaily]
    serializer_class = RegistrationSerializer
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save(user=request.user if request.user.is_authenticated else None)
        return Response({'id': item.pk, 'session': item.session_id, 'status': 'registered'}, status=201)
