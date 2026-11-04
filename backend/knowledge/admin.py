from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from accounts.permissions import has_role
from intake.admin import FirmMemberAdmin
from .models import Jurisdiction, RightsTopic, KnowledgeArticle, FAQ
from .services import review_content
from .models import HelpContact, GuidedFlow, GuidedQuestion, GuidedOption
from django.utils import timezone


@admin.register(Jurisdiction)
class JurisdictionAdmin(FirmMemberAdmin):
    list_display = ('name', 'code', 'is_active')
    search_fields = ('name', 'code')


@admin.register(RightsTopic)
class TopicAdmin(FirmMemberAdmin):
    list_display = ('title', 'slug', 'is_active')
    search_fields = ('title', 'slug')


class ReviewedAdmin(FirmMemberAdmin):
    readonly_fields = ('status', 'reviewed_by', 'reviewed_at', 'created_at', 'updated_at')
    list_filter = ('status', 'jurisdiction', 'language', 'is_sample')
    actions = ['mark_reviewed', 'publish']

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not has_role(request.user, 'admin', 'lawyer'):
            actions.pop('mark_reviewed', None)
            actions.pop('publish', None)
        return actions

    def review_selected(self, request, queryset, publish):
        if not has_role(request.user, 'admin', 'lawyer'):
            return
        for item in queryset:
            try:
                review_content(self.model, item.pk, request.user, publish=publish)
            except ValidationError as error:
                self.message_user(request, ' '.join(error.messages), messages.ERROR)

    @admin.action(description='Mark selected content reviewed', permissions=['change'])
    def mark_reviewed(self, request, queryset):
        self.review_selected(request, queryset, False)

    @admin.action(description='Publish selected reviewed content', permissions=['change'])
    def publish(self, request, queryset):
        self.review_selected(request, queryset, True)


@admin.register(KnowledgeArticle)
class ArticleAdmin(ReviewedAdmin):
    list_display = ('title', 'language', 'status', 'is_sample')
    search_fields = ('title', 'slug')


@admin.register(FAQ)
class FAQAdmin(ReviewedAdmin):
    list_display = ('question', 'language', 'status', 'is_sample')
    search_fields = ('question',)


@admin.register(HelpContact)
class ContactAdmin(FirmMemberAdmin):
    list_display = ('label', 'phone', 'is_emergency', 'verified_at')
    readonly_fields = ('verified_by', 'verified_at')
    actions = ['record_verification']

    @admin.action(description='Record supervisor verification (reference required)', permissions=['change'])
    def record_verification(self, request, queryset):
        if not has_role(request.user, 'admin'):
            self.message_user(request, 'Only an admin may record verification.', messages.ERROR)
            return
        for contact in queryset:
            if not contact.verification_reference:
                self.message_user(request, 'Add the supervisor verification reference first.', messages.ERROR)
                continue
            contact.verified_by, contact.verified_at = request.user, timezone.now()
            contact.save()


@admin.register(GuidedFlow)
class FlowAdmin(FirmMemberAdmin):
    list_display = ('name', 'purpose', 'is_active', 'is_sample')
    search_fields = ('name',)


@admin.register(GuidedQuestion)
class QuestionAdmin(FirmMemberAdmin):
    list_display = ('text', 'flow', 'order')
    list_filter = ('flow',)
    search_fields = ('text',)


@admin.register(GuidedOption)
class OptionAdmin(FirmMemberAdmin):
    list_display = ('label', 'question', 'next_question', 'escalate_to_consultation')
    search_fields = ('label',)
