"""Start the single-instance Render demonstration. Never print credentials."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.render')
import django
django.setup()
from django.conf import settings
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from waitress import serve

call_command('migrate', interactive=False)
call_command('createcachetable', verbosity=0)
call_command('bootstrap_demo')

serve(get_wsgi_application(), host='0.0.0.0', port=int(os.environ.get('PORT', '10000')),
      threads=4, clear_untrusted_proxy_headers=False)
