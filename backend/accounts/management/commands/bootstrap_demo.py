"""Create a demo administrator once, without exposing or resetting credentials."""
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction


class Command(BaseCommand):
    help = 'Bootstrap the explicitly enabled hosted fictional demo.'

    def handle(self, *args, **options):
        if not getattr(settings, 'ALLOW_DEMO_SEED', False):
            raise CommandError('Hosted demo bootstrap is disabled in this settings profile.')
        username = os.environ.get('DEMO_ADMIN_USERNAME', '')
        password = os.environ.get('DEMO_ADMIN_PASSWORD', '')
        if not username:
            raise CommandError('Set DEMO_ADMIN_USERNAME for the hosted demo.')
        User = get_user_model()
        with transaction.atomic():
            user = User.objects.filter(username=username).first()
            if user is None:
                if not password:
                    raise CommandError('Set DEMO_ADMIN_PASSWORD for the first deployment.')
                validate_password(password, User(username=username))
                user = User.objects.create_superuser(username=username, password=password)
            if user.role != 'admin' or not user.is_active or not user.is_superuser:
                raise CommandError('Demo username conflicts with an existing non-admin account.')
        # Existing credentials are never changed, including after the secret is removed.
        call_command('seed_demo', created_by=username, stdout=self.stdout)
