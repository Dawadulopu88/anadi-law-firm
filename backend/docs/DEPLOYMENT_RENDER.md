# Deployment

## Settings profiles

| Profile | Database | Intended use |
|---|---|---|
| `config.settings` | MySQL by default; optional PostgreSQL URL | Local development |
| `config.production` | MySQL or PostgreSQL | Managed HTTPS deployment with persistent storage |
| `config.render` | PostgreSQL with TLS | Temporary Render demonstration |

Set `DJANGO_SETTINGS_MODULE` explicitly in the hosting environment. Do not use
Django's development server for a public deployment. Deployment credentials and
data are environment-specific and must not be stored in this repository.

## Managed HTTPS deployment

1. Install `requirements-production.txt` for MySQL, or `requirements-render.txt`
   for the PostgreSQL driver and WSGI dependencies.
2. Use `deploy/production.env.example` as a configuration template. Set a new
   random `PRODUCTION_SECRET_KEY` of at least 50 characters, explicit
   `PRODUCTION_ALLOWED_HOSTS`, exact HTTPS CORS/CSRF origins, and database credentials.
   The shared settings import also requires `SECRET_KEY`; use the same secure value.
3. Set `PRODUCTION_DATA_ROOT` to an absolute persistent directory writable by the
   application account. Public branding, private documents, and static assets
   occupy separate subdirectories. Never serve private storage as a public directory.
4. Configure a valid TLS certificate and reverse proxy. The nginx template assumes
   nginx and Waitress run on the same host. Replace every example domain and path.
5. Run the management commands below under `DJANGO_SETTINGS_MODULE=config.production`.
6. Start Waitress under a service/process manager and verify the actual external URL.

```text
python manage.py check --deploy
python manage.py migrate --noinput
python manage.py createcachetable
python manage.py collectstatic --noinput
python manage.py createsuperuser
waitress-serve --listen=127.0.0.1:8001 --trusted-proxy=127.0.0.1 --trusted-proxy-count=1 --trusted-proxy-headers="x-forwarded-for x-forwarded-proto" config.wsgi:application
```

The proxy must overwrite incoming forwarding headers. Waitress trusts only the
configured proxy and normalizes the request scheme/client address. Review this
configuration when changing the network topology. The database-backed cache shares
throttle state across application processes; it is not an edge DDoS protection service.

HTTPS redirection, secure session/CSRF cookies, HSTS, content-type protection and
strict host validation are enabled. HSTS subdomains and preload remain opt-in:
deployment checks report W005/W021 until the domain owner enables them. Enable
these only after verifying HTTPS coverage for the relevant domains.

## Optional Render demonstration

The root `render.yaml` defines a free Python web service and free PostgreSQL
database. It targets `main`. This profile uses fictional records only; it is not
a durable storage arrangement for client operations.

Render's free services have idle shutdown, temporary filesystems, database expiry,
and backup limitations. Review [the current free-service limits](https://render.com/docs/free)
and the database expiration date before provisioning. Use persistent database and
file storage for operational deployments.

### Provisioning

1. In Render, create a Blueprint from the backend repository and select `main`.
2. Grant repository access through the organisation's approved integration process.
3. Review both service plans and all proposed resources before applying the Blueprint.
4. Set a strong `DEMO_ADMIN_PASSWORD` privately. The initial username is `demo_admin`.
5. Apply the Blueprint and inspect build/deployment logs until the service is healthy.
6. Use the assigned HTTPS `*.onrender.com` URL; a custom domain is not required.

The build installs `requirements-render.txt` and collects static files. Startup
applies migrations, creates the shared cache table and runs `bootstrap_demo`.
The command validates the initial password, refuses conflicting non-admin users,
and preserves existing passwords. It then seeds linked fictional records.
`DEBUG` remains False. WhiteNoise serves static assets, including Admin CSS.

After confirming initial administrator access, remove `DEMO_ADMIN_PASSWORD` from
the service environment and redeploy. Keep `DEMO_ADMIN_USERNAME`. Existing credentials
remain unchanged; a replacement empty database requires a new initial password.
Use authenticated Admin account management for subsequent password changes.

### Frontend origins and forwarded headers

Set `PRODUCTION_CORS_ALLOWED_ORIGINS` to the exact HTTPS frontend origin, without a
trailing slash. Comma-separated origins are supported; wildcard origins are rejected.
Redeploy after configuration changes. Never expose database credentials or Django
secrets through frontend configuration.

The Render profile expects its managed ingress to control forwarded scheme/IP
headers. Do not reuse it on a directly exposed server or add an extra proxy without
reviewing trusted-header handling. Refer to
[Render's Django deployment documentation](https://render.com/docs/deploy-django).

## Deployment verification

| Request or operation | Expected result |
|---|---|
| `/admin/` | Styled login form or authenticated administration |
| `/api/courses/` | HTTP 200 with public JSON; exercises the database |
| `/api/auth/me/` without a token | HTTP 401 |
| `/private_media/example.txt` | HTTP 404 |
| `/` | HTTP 404; no frontend homepage is configured |
| Invalid host | Rejected without application data |
| Invalid input | Validation response without a developer traceback |
| Private document download | Available only with the required record access |

Verify CORS with the actual frontend origin and test the visitor, staff, lawyer,
and client workflows. Check another client's access and hidden document behaviour.
Review application logs without exposing tokens, tracking codes or confidential data.

## Backup and restoration

Database backups and uploaded-file backups are separate requirements. Store both
outside the web root with restricted access and defined retention. Monitor backup
completion and periodically restore into an isolated environment.

For PostgreSQL, use command-line tools matching the server's major version or
newer. Use the external connection host when backing up a hosted database from a
workstation. Supply the password through the interactive prompt rather than a
command-line URL. In PowerShell, set `$env:PGSSLMODE='require'` for a hosted TLS connection.

```text
pg_dump --host=DATABASE_HOST --port=5432 --username=DATABASE_USER --dbname=DATABASE_NAME --password --format=custom --file=backend-backup.dump
```

Restore into a newly created empty database, never over an active environment:

```text
pg_restore --host=RESTORE_HOST --port=5432 --username=RESTORE_USER --dbname=EMPTY_RESTORE_DATABASE --password --no-owner --no-privileges backend-backup.dump
```

For MySQL, use the approved backup service or a consistent `mysqldump` export
(the example assumes InnoDB tables and no concurrent schema changes):

```text
mysqldump --host=DATABASE_HOST --port=3306 --user=BACKUP_USER --password --single-transaction --no-tablespaces --result-file=backend-backup.sql DATABASE_NAME
```

Import the dump into a new empty recovery database using the MySQL client or the
organisation's restore tooling. Restore the corresponding public/private files,
configure the isolated application's storage paths, then verify a known record,
invoice balance, authenticated document download and permission boundaries.
Backups contain sensitive records and password hashes and must not be committed.

On free Render instances, uploaded files can disappear after restart or redeploy.
Retain source files for fictional demonstrations and re-upload as a new document
version if necessary. A database restore alone cannot recover those file bytes.

## Operational requirements

Before accepting real client records, establish durable storage, database/file
backup schedules, monitoring, incident ownership, upload-scanning policy, content
review, and frontend acceptance testing. These activities are not performed by
applying a deployment template or passing the automated test suite.
