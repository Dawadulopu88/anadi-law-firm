from django.templatetags.static import static
from django.utils.translation import get_language
from rest_framework import serializers

from .models import FirmProfile, LawyerProfile, PracticeArea


def localized(obj, field):
    if (get_language() or 'en').split('-')[0] == 'bn':
        translated = getattr(obj, field + '_bn', '')
        if translated:
            return translated
    return getattr(obj, field)


class LocalizedSerializer(serializers.ModelSerializer):
    localized_fields = ()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in self.localized_fields:
            data[field] = localized(instance, field)
        return data


class FirmProfileSerializer(LocalizedSerializer):
    logo = serializers.SerializerMethodField()
    localized_fields = ('name', 'tagline', 'about', 'address', 'working_hours')

    class Meta:
        model = FirmProfile
        fields = (
            'name', 'tagline', 'about', 'address', 'phone', 'email', 'logo',
            'working_hours', 'website_url', 'facebook_url', 'linkedin_url',
        )

    def get_logo(self, obj):
        url = obj.logo.url if obj.logo else static('firm/anadi-law-firm.png')
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url


class PracticeAreaSerializer(LocalizedSerializer):
    localized_fields = ('name', 'description')

    class Meta:
        model = PracticeArea
        fields = ('id', 'name', 'slug', 'description', 'icon', 'display_order')


class LawyerProfileSerializer(LocalizedSerializer):
    full_name = serializers.SerializerMethodField()
    practice_areas = serializers.SerializerMethodField()
    localized_fields = ('title', 'bio', 'languages')

    class Meta:
        model = LawyerProfile
        fields = (
            'id', 'full_name', 'photo', 'title', 'bio',
            'practice_areas', 'experience_years', 'languages',
        )

    def get_full_name(self, obj):
        if (get_language() or 'en').split('-')[0] == 'bn' and obj.full_name_bn:
            return obj.full_name_bn
        return obj.user.get_full_name()

    def get_practice_areas(self, obj):
        # Use the filtered prefetch; never leak inactive areas through nesting.
        return PracticeAreaSerializer(
            obj.public_practice_areas, many=True, context=self.context,
        ).data
