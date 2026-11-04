from rest_framework.routers import SimpleRouter

from .views import ClientViewSet
from .portal import PortalViewSet

app_name = 'clients'
router = SimpleRouter()
router.register('clients', ClientViewSet, basename='client')
router.register('portal', PortalViewSet, basename='portal')
urlpatterns = router.urls
