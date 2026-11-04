"""Authentication and public firm content routes."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from accounts.token_views import LimitedTokenObtainPairView, LimitedTokenRefreshView

urlpatterns = [
    path('api/', include('academy.urls')),
    path('api/', include('billing.urls')),
    path('api/', include('legalaid.urls')),
    path('api/', include('documents.urls')),
    path('api/', include('knowledge.urls')),
    path('api/', include('cases.urls')),
    path('api/', include('intake.urls')),
    path('api/auth/', include('accounts.urls')),
    path('api/', include('accounts.user_urls')),
    path('api/', include('clients.urls')),
    path('api/', include('firm.urls')),
    path('admin/', admin.site.urls),
    path('api/auth/token/', LimitedTokenObtainPairView.as_view(), name='token_obtain'),
    path('api/auth/token/refresh/', LimitedTokenRefreshView.as_view(), name='token_refresh'),
]

# Development-only public branding uploads. Never expose PRIVATE_MEDIA_ROOT.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif getattr(settings, 'SERVE_DEMO_BRANDING', False):
    from firm.media import public_brand_image
    urlpatterns += [path('media/<path:name>', public_brand_image, name='demo-public-brand-image')]
