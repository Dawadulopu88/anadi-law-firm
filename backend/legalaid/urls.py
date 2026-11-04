from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ApplyView, TrackView, ApplicationViewSet
router = DefaultRouter()
router.register('legal-aid/applications', ApplicationViewSet, basename='legal-aid-application')
urlpatterns = [path('legal-aid/apply/', ApplyView.as_view()), path('legal-aid/track/<str:code>/', TrackView.as_view())] + router.urls
