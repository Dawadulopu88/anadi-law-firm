from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import PathwayViewSet, CourseViewSet, SessionViewSet, RegistrationView
router = DefaultRouter()
router.register('pathways', PathwayViewSet)
router.register('courses', CourseViewSet, basename='course')
router.register('live-sessions', SessionViewSet, basename='live-session')
urlpatterns = [path('session-registrations/', RegistrationView.as_view())] + router.urls
