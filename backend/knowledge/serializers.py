from django.utils.translation import get_language
from rest_framework import serializers
from firm.serializers import LocalizedSerializer
from .models import Jurisdiction, RightsTopic, KnowledgeArticle, FAQ


def disclaimer():
    if (get_language() or 'en').startswith('bn'):
        return 'এটি সাধারণ তথ্য, আইনি পরামর্শ নয়। আপনার পরিস্থিতির জন্য যোগ্য আইনজীবীর পরামর্শ নিন। নমুনা বিষয়বস্তু বাস্তব নির্দেশনা নয়।'
    return 'General information, not legal advice. Consult a qualified lawyer about your circumstances. Sample content is for demonstration only.'


class JurisdictionSerializer(LocalizedSerializer):
    localized_fields = ('name',)
    class Meta:
        model = Jurisdiction
        fields = ('id', 'name', 'code', 'flag', 'is_active')


class TopicSerializer(LocalizedSerializer):
    localized_fields = ('title', 'description')
    class Meta:
        model = RightsTopic
        fields = ('id', 'title', 'slug', 'icon', 'description', 'practice_area')


class DisclaimerSerializer(serializers.ModelSerializer):
    disclaimer = serializers.SerializerMethodField()
    def get_disclaimer(self, obj):
        return disclaimer()


class ArticleSerializer(DisclaimerSerializer):
    class Meta:
        model = KnowledgeArticle
        fields = ('id', 'jurisdiction', 'topic', 'title', 'slug', 'summary', 'body', 'source_reference', 'language', 'is_sample', 'reviewed_at', 'updated_at', 'disclaimer')


class FAQSerializer(DisclaimerSerializer):
    class Meta:
        model = FAQ
        fields = ('id', 'topic', 'jurisdiction', 'question', 'answer', 'language', 'is_sample', 'disclaimer')
