import os
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings


@override_settings(ALLOW_DEMO_SEED=True)
class HostedDemoBootstrapTests(TestCase):
    def run_bootstrap(self, password='Example-test-only-password-782!'):
        with patch.dict(os.environ, {'DEMO_ADMIN_USERNAME': 'hosted_demo_admin',
                                     'DEMO_ADMIN_PASSWORD': password}):
            call_command('bootstrap_demo', stdout=StringIO())

    @override_settings(ALLOW_DEMO_SEED=False)
    def test_disabled_outside_explicit_demo_profile(self):
        with self.assertRaises(CommandError):
            self.run_bootstrap()
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_rejects_missing_and_weak_initial_passwords(self):
        with self.assertRaises(CommandError):
            self.run_bootstrap('')
        with self.assertRaises(ValidationError):
            self.run_bootstrap('123')
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_preserves_existing_password_and_seeds_after_secret_removed(self):
        with patch('accounts.management.commands.bootstrap_demo.call_command') as seed:
            self.run_bootstrap()
            user = get_user_model().objects.get(username='hosted_demo_admin')
            original = user.password
            self.assertTrue(user.is_superuser)
            self.assertEqual(user.role, 'admin')
            self.run_bootstrap('')
            user.refresh_from_db()
            self.assertEqual(user.password, original)
            self.assertEqual(seed.call_count, 2)

    def test_never_promotes_conflicting_user(self):
        user = get_user_model().objects.create_user(username='hosted_demo_admin', role='client')
        with self.assertRaises(CommandError):
            self.run_bootstrap()
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.role, 'client')
