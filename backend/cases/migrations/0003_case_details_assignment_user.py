from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('cases', '0002_hearing_task')]

    operations = [
        migrations.AddField('case', 'court', models.CharField(max_length=200, blank=True)),
        migrations.AddField('case', 'opposite_party', models.CharField(max_length=250, blank=True)),
        migrations.AddField('case', 'priority', models.CharField(max_length=10, choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High')], default='normal')),
        migrations.AddField('case', 'closed_date', models.DateField(null=True, blank=True)),
        migrations.RemoveConstraint('caseassignment', 'cases_unique_assignment'),
        migrations.RenameField('caseassignment', 'lawyer', 'user'),
        migrations.AlterField('caseassignment', 'user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT, related_name='case_assignments', limit_choices_to={'role__in': ['lawyer', 'staff']})),
        migrations.AddField('caseassignment', 'role', models.CharField(max_length=10, choices=[('lead', 'Lead'), ('support', 'Support')], default='support')),
        migrations.AddConstraint('caseassignment', models.UniqueConstraint(fields=('case', 'user'), name='cases_unique_assignment')),
    ]
