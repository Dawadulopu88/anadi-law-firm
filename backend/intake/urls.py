from rest_framework.routers import SimpleRouter

from .views import AppointmentViewSet, ConsultationViewSet

app_name = 'intake'
router = SimpleRouter()
router.register('consultations', ConsultationViewSet, basename='consultation')
router.register('appointments', AppointmentViewSet, basename='appointment')
urlpatterns = router.urls
