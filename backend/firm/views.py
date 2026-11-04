from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import FirmProfile, LawyerProfile, PracticeArea
from .serializers import FirmProfileSerializer, LawyerProfileSerializer, PracticeAreaSerializer


class FirmProfileDetail(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = FirmProfileSerializer

    def get_object(self):
        return get_object_or_404(FirmProfile, pk=1)


class PracticeAreaList(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = PracticeAreaSerializer
    queryset = PracticeArea.objects.filter(is_active=True)


class PracticeAreaDetail(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PracticeAreaSerializer
    queryset = PracticeArea.objects.filter(is_active=True)
    lookup_field = 'slug'


class PublicLawyerQueryset:
    def get_queryset(self):
        return LawyerProfile.objects.filter(
            is_public=True, user__is_active=True, user__role='lawyer',
        ).select_related('user').prefetch_related(Prefetch(
            'practice_areas',
            queryset=PracticeArea.objects.filter(is_active=True),
            to_attr='public_practice_areas',
        ))


class LawyerList(PublicLawyerQueryset, generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = LawyerProfileSerializer


class LawyerDetail(PublicLawyerQueryset, generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = LawyerProfileSerializer
