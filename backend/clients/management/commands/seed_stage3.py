from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.permissions import is_firm_member
from clients.models import Client


class Command(BaseCommand):
    help = 'Create optional Stage 3 demo users/clients with no usable login passwords.'

    def add_arguments(self, parser):
        parser.add_argument('--created-by', required=True, help='Existing active firm-member username.')

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        actor = User.objects.filter(username=options['created_by']).first()
        if not is_firm_member(actor):
            raise CommandError('--created-by must name an existing active admin, lawyer or staff user.')
        for suffix, role in [('staff', 'staff'), ('lawyer', 'lawyer'), ('client_one', 'client'), ('client_two', 'client')]:
            username = 'stage3_demo_' + suffix
            user, created = User.objects.get_or_create(username=username, defaults={
                'role': role, 'first_name': 'Sample', 'last_name': suffix.replace('_', ' ').title(),
            })
            if created:
                user.set_unusable_password()
                user.save(update_fields=['password'])
            elif not user.is_active or user.role != role:
                raise CommandError(f'{username} has a conflicting role/status. No demo data was changed.')
            if role == 'client':
                Client.objects.get_or_create(user=user, defaults={
                    'full_name': user.get_full_name(),
                    'notes': 'Internal demo note. This must never appear in client-role API responses.',
                    'created_by': actor,
                })
        self.stdout.write(self.style.SUCCESS(
            'Stage 3 demo records ready. Existing data/passwords preserved. '
            'New demo users have no usable passwords; set local passwords with changepassword when needed.'
        ))
