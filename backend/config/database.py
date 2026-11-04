from urllib.parse import parse_qs, unquote, urlsplit
from django.core.exceptions import ImproperlyConfigured


def postgres_database(url):
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in ('postgres', 'postgresql') or not parsed.hostname or not parsed.path.strip('/'):
            raise ValueError
        options = parse_qs(parsed.query)
        sslmode = options.get('sslmode', ['require'])[0]
        if sslmode not in ('require', 'verify-ca', 'verify-full', 'disable'):
            raise ValueError
        return {'ENGINE': 'django.db.backends.postgresql', 'NAME': unquote(parsed.path[1:]),
                'USER': unquote(parsed.username or ''), 'PASSWORD': unquote(parsed.password or ''),
                'HOST': parsed.hostname, 'PORT': parsed.port or 5432,
                'CONN_MAX_AGE': 60, 'CONN_HEALTH_CHECKS': True, 'OPTIONS': {'sslmode': sslmode}}
    except (ValueError, TypeError):
        # Do not include a connection URL containing a password in an exception.
        raise ImproperlyConfigured('DATABASE_URL must be a valid PostgreSQL connection URL.') from None
