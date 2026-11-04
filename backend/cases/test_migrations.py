from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class AssignmentMigrationTests(TransactionTestCase):
    def test_existing_lawyer_assignment_survives_column_rename(self):
        old_target = [('cases', '0002_hearing_task')]
        new_target = [('cases', '0003_case_details_assignment_user')]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        try:
            apps = executor.loader.project_state(old_target).apps
            User = apps.get_model('accounts', 'User')
            actor = User.objects.create(username='migration_admin', role='admin')
            lawyer = User.objects.create(username='migration_lawyer', role='lawyer')
            client = apps.get_model('clients', 'Client').objects.create(full_name='Migration sample', created_by_id=actor.pk)
            area = apps.get_model('firm', 'PracticeArea').objects.create(name='Migration sample', slug='migration')
            case = apps.get_model('cases', 'Case').objects.create(case_number='MIG-1', title='Sample', client_id=client.pk, practice_area_id=area.pk, created_by_id=actor.pk)
            assignment = apps.get_model('cases', 'CaseAssignment').objects.create(case_id=case.pk, lawyer_id=lawyer.pk, assigned_by_id=actor.pk)
            executor = MigrationExecutor(connection)
            executor.migrate(new_target)
            apps = executor.loader.project_state(new_target).apps
            restored = apps.get_model('cases', 'CaseAssignment').objects.get(pk=assignment.pk)
            self.assertEqual(restored.user_id, lawyer.pk)
            self.assertEqual(restored.case_id, case.pk)
            self.assertEqual(restored.assigned_by_id, actor.pk)
            self.assertEqual(restored.role, 'support')
            self.assertEqual(apps.get_model('cases', 'Case').objects.get(pk=case.pk).priority, 'normal')
        finally:
            MigrationExecutor(connection).migrate(new_target)
