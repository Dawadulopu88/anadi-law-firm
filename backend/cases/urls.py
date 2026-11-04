from rest_framework.routers import DefaultRouter
from .views import CaseViewSet, CaseAssignmentViewSet, CaseNoteViewSet
from .work import HearingViewSet, TaskViewSet

router = DefaultRouter()
router.register('cases', CaseViewSet, basename='case')
router.register('case-assignments', CaseAssignmentViewSet, basename='case-assignment')
router.register('case-notes', CaseNoteViewSet, basename='case-note')
router.register('hearings', HearingViewSet, basename='hearing')
router.register('tasks', TaskViewSet, basename='task')
urlpatterns = router.urls
