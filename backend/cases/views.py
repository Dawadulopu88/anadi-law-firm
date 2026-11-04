from rest_framework import filters, mixins, serializers, viewsets

from accounts.permissions import has_role
from .models import Case, CaseAssignment, CaseNote
from .permissions import CanAccessCases, CanAccessNotes, CanManageAssignments, visible_cases
from .serializers import CaseSerializer, OwnCaseSerializer, CaseAssignmentSerializer, CaseNoteSerializer, OwnCaseNoteSerializer


def filter_id(queryset, params, field):
    if field in params:
        try:
            value = int(params[field])
            if value <= 0 or value > 2147483647:
                raise ValueError
        except (ValueError, TypeError):
            raise serializers.ValidationError({field: 'Use a positive integer ID.'})
        queryset = queryset.filter(**{field: value})
    return queryset


class CaseViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [CanAccessCases]
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['case_number', 'title']
    ordering_fields = ['created_at', 'updated_at', 'filing_date', 'case_number']

    def get_queryset(self):
        queryset = visible_cases(self.request.user)
        params = self.request.query_params
        for field in ('client', 'practice_area'):
            queryset = filter_id(queryset, params, field)
        if 'status' in params:
            if params['status'] not in Case.Status.values:
                raise serializers.ValidationError({'status': 'Unknown case status.'})
            queryset = queryset.filter(status=params['status'])
        if 'lawyer' in params:
            assignments = filter_id(CaseAssignment.objects.all(), {'user': params['lawyer']}, 'user').filter(user__role='lawyer')
            queryset = queryset.filter(pk__in=assignments.values('case_id'))
        return queryset

    def get_serializer_class(self):
        return OwnCaseSerializer if has_role(self.request.user, 'client') else CaseSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class CaseAssignmentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    permission_classes = [CanManageAssignments]
    serializer_class = CaseAssignmentSerializer
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        queryset = CaseAssignment.objects.filter(case__in=visible_cases(self.request.user))
        return filter_id(queryset, self.request.query_params, 'case')

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)


class CaseNoteViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [CanAccessNotes]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        queryset = CaseNote.objects.filter(case__in=visible_cases(self.request.user))
        if has_role(self.request.user, 'client'):
            queryset = queryset.filter(is_internal=False)
        return filter_id(queryset, self.request.query_params, 'case')

    def get_serializer_class(self):
        return OwnCaseNoteSerializer if has_role(self.request.user, 'client') else CaseNoteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
