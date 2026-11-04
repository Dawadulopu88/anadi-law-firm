from django.urls import path

from .users import ChangePasswordView
from .views import CurrentUserView

app_name = 'accounts'
urlpatterns = [
    path('me/', CurrentUserView.as_view(), name='me'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
]
