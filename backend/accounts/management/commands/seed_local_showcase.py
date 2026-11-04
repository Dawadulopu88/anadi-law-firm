"""Local-only showcase: demo data + login passwords you choose + published sample knowledge.

Usage (DEBUG=True only):
    python manage.py seed_local_showcase --password "Your-Local-Pass-123!"

Creates/keeps an `admin` superuser, runs `seed_demo`, sets the given password on the
admin and the stage3 demo accounts, and publishes the labelled sample knowledge so the
public website has content. Never run against shared or production data.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction
from django.utils import timezone

from firm.models import FirmProfile
from knowledge.models import FAQ, KnowledgeArticle

DEMO_USERNAMES = ('stage3_demo_staff', 'stage3_demo_lawyer', 'stage3_demo_client_one', 'stage3_demo_client_two')


class Command(BaseCommand):
    help = 'Local development only: seed demo data and set local login passwords.'

    def add_arguments(self, parser):
        parser.add_argument('--password', required=True, help='Password for admin and demo logins (local only).')
        parser.add_argument('--admin-username', default='admin')

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('seed_local_showcase only runs with DEBUG=True on a local database.')
        User = get_user_model()
        password = options['password']
        username = options['admin_username']
        validate_password(password, User(username=username))
        with transaction.atomic():
            admin = User.objects.filter(username=username).first()
            if admin is None:
                admin = User.objects.create_superuser(username=username, password=password,
                                                      first_name='Firm', last_name='Administrator')
            elif admin.role != 'admin':
                raise CommandError(f'{username} exists without the admin role.')
            else:
                admin.set_password(password)
                admin.save(update_fields=['password'])
        call_command('seed_demo', created_by=username, stdout=self.stdout)
        with transaction.atomic():
            for name in DEMO_USERNAMES:
                user = User.objects.get(username=name)
                user.set_password(password)
                user.save(update_fields=['password'])
            profile = FirmProfile.objects.get(pk=1)
            for field, value in {
                'address': 'Sample address, Dhaka, Bangladesh (replace before publication)',
                'address_bn': 'নমুনা ঠিকানা, ঢাকা, বাংলাদেশ',
                'working_hours': 'Sun–Thu, 10:00 AM – 6:00 PM',
                'working_hours_bn': 'রবি–বৃহস্পতি, সকাল ১০টা – সন্ধ্যা ৬টা',
                'email': 'info@example.test',
            }.items():
                if not getattr(profile, field):
                    setattr(profile, field, value)
            profile.save()
            now = timezone.now()
            for model in (KnowledgeArticle, FAQ):
                for item in model.objects.filter(is_sample=True, status='draft'):
                    item.status, item.reviewed_by, item.reviewed_at = 'reviewed', admin, now
                    item.save()
                    item.status = 'published'
                    item.save()
        call_command('seed_guided_help', stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS(
            f'Local showcase ready. Logins (password as given): {username} (admin), '
            + ', '.join(f'{n}' for n in DEMO_USERNAMES)
        ))
