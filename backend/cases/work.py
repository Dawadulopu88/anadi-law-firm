from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from accounts.permissions import IsFirmMember, has_role
from .models import Hearing, Task
from .permissions import CanAccessNotes, visible_cases
from .serializers import AccessibleCaseSerializer
from .views import filter_id


def visible_tasks(user):
    queryset = Task.objects.all()
    if has_role(user, 'admin', 'staff'):
        return queryset
    if has_role(user, 'lawyer'):
        return queryset.filter(Q(case__in=visible_cases(user)) | Q(case__isnull=True, assigned_to=user))
    return queryset.none()


class HearingSerializer(AccessibleCaseSerializer):
    class Meta:
        model = Hearing
        fields = ('id', 'case', 'court_name', 'hearing_at', 'case_number', 'outcome', 'next_hearing_date', 'notes', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class OwnHearingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hearing
        fields = ('id', 'case', 'court_name', 'hearing_at', 'case_number', 'outcome', 'next_hearing_date')
        read_only_fields = fields


class TaskSerializer(AccessibleCaseSerializer):
    class Meta:
        model = Task
        fields = ('id', 'case', 'title', 'description', 'priority', 'due_date', 'status', 'assigned_to', 'created_by', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')

    def validate(self, attrs):
        user = self.context['request'].user
        case = attrs.get('case', self.instance.case if self.instance else None)
        assignee = attrs.get('assigned_to', self.instance.assigned_to if self.instance else None)
        if has_role(user, 'lawyer') and case is None and assignee != user:
            raise serializers.ValidationError('A lawyer can only assign standalone tasks to themselves.')
        return attrs


class HearingViewSet(viewsets.ModelViewSet):
    permission_classes = [CanAccessNotes]
    def get_queryset(self):
        return filter_id(Hearing.objects.filter(case__in=visible_cases(self.request.user)), self.request.query_params, 'case')

    def get_serializer_class(self):
        return OwnHearingSerializer if has_role(self.request.user, 'client') else HearingSerializer

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        data = self.paginate_queryset(self.get_queryset().filter(hearing_at__gte=timezone.now()))
        return self.get_paginated_response(self.get_serializer(data, many=True).data)


class TaskViewSet(viewsets.ModelViewSet):
    permission_classes = [IsFirmMember]
    serializer_class = TaskSerializer
    def get_queryset(self):
        return filter_id(visible_tasks(self.request.user), self.request.query_params, 'case')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'], url_path='my-tasks')
    def my_tasks(self, request):
        data = self.paginate_queryset(self.get_queryset().filter(assigned_to=request.user))
        return self.get_paginated_response(self.get_serializer(data, many=True).data)
