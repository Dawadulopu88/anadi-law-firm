from django.contrib import admin
from intake.admin import FirmMemberAdmin
from .models import Pathway, Course, LiveSession, SessionRegistration


@admin.register(Pathway)
class PathwayAdmin(FirmMemberAdmin):
    list_display = ('title', 'is_active', 'is_sample')
    search_fields = ('title', 'slug')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Course)
class CourseAdmin(FirmMemberAdmin):
    list_display = ('title', 'pathway', 'level', 'is_published')
    list_filter = ('is_published', 'pathway', 'level')
    search_fields = ('title',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(LiveSession)
class SessionAdmin(FirmMemberAdmin):
    list_display = ('title', 'start', 'capacity', 'seats_remaining', 'is_published')
    search_fields = ('title',)
    readonly_fields = ('created_at', 'updated_at', 'seats_remaining')


@admin.register(SessionRegistration)
class RegistrationAdmin(FirmMemberAdmin):
    list_display = ('session', 'name', 'email', 'created_at')
    list_filter = ('session',)
    search_fields = ('name', 'email')
    readonly_fields = ('created_at', 'updated_at')
    def delete_queryset(self, request, queryset):
        for obj in queryset.order_by('session_id', 'pk'):
            obj.delete()
