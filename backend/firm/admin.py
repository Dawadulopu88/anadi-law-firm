from django.contrib import admin

from .models import FirmProfile, LawyerProfile, PracticeArea


@admin.register(FirmProfile)
class FirmProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('English content', {'fields': ('name', 'tagline', 'about', 'address', 'working_hours')}),
        ('Bangla content', {'fields': ('name_bn', 'tagline_bn', 'about_bn', 'address_bn', 'working_hours_bn')}),
        ('Contact and branding', {'fields': ('phone', 'email', 'logo', 'website_url', 'facebook_url', 'linkedin_url')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    def has_add_permission(self, request):
        return super().has_add_permission(request) and not FirmProfile.objects.exists()


@admin.register(PracticeArea)
class PracticeAreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'display_order', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'name_bn', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('display_order', 'is_active')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(LawyerProfile)
class LawyerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'experience_years', 'is_public', 'updated_at')
    list_filter = ('is_public', 'practice_areas')
    search_fields = ('user__first_name', 'user__last_name', 'full_name_bn', 'title')
    # Keep profile editing independent of account-administration permission.
    filter_horizontal = ('practice_areas',)
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('user',)
