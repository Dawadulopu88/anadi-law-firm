from django.urls import path

from . import views

app_name = 'firm'

urlpatterns = [
    path('firm/profile/', views.FirmProfileDetail.as_view(), name='profile'),
    path('practice-areas/', views.PracticeAreaList.as_view(), name='practice-area-list'),
    path('practice-areas/<slug:slug>/', views.PracticeAreaDetail.as_view(), name='practice-area-detail'),
    path('lawyers/', views.LawyerList.as_view(), name='lawyer-list'),
    path('lawyers/<int:pk>/', views.LawyerDetail.as_view(), name='lawyer-detail'),
]
