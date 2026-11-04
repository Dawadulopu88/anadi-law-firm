from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import JurisdictionViewSet, TopicViewSet, ArticleViewSet, FAQViewSet, SearchView
from .guided import FlowViewSet, QuestionDetail, ResultView, ContactList

router = DefaultRouter()
router.register('jurisdictions', JurisdictionViewSet)
router.register('rights-topics', TopicViewSet)
router.register('articles', ArticleViewSet, basename='article')
router.register('faqs', FAQViewSet, basename='faq')
router.register('guided-flows', FlowViewSet, basename='guided-flow')
urlpatterns = [path('knowledge/search/', SearchView.as_view()),
               path('help-contacts/', ContactList.as_view()),
               path('guided-questions/<int:pk>/', QuestionDetail.as_view()),
               path('guided-options/<int:pk>/result/', ResultView.as_view())] + router.urls
