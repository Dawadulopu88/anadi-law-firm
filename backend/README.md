# Anadi Law Firm Backend

Django REST API for law-firm operations, public information, legal-aid intake,
Academy listings, and client access. Django Admin provides internal administration
for authorised users. The customer-facing application is maintained in the separate
[frontend repository](https://github.com/Cyber-Bit-Byte/law-firm-frontend).

## Features

- **Identity and access:** JWT authentication, admin/staff/lawyer/client roles,
  account administration, and record-level permission checks.
- **Firm content:** firm profile, practice areas, lawyer profiles, and public branding.
- **Client intake:** client records, consultation submissions, conversion to clients,
  and appointments with scheduling validation.
- **Case management:** case details, lead/support assignments, internal/shared notes,
  hearings, and assigned tasks.
- **Documents:** validated uploads, document versions, client visibility controls,
  and authenticated downloads from private storage.
- **Knowledge:** jurisdictions, rights topics, reviewed articles, FAQs, search,
  structured guided-help flows, and verified support contacts.
- **Billing and legal aid:** invoices, manual payment records, outstanding balances,
  legal-aid applications, and private application tracking.
- **Academy:** learning pathways, course listings, live sessions, and registrations
  with capacity and duplicate checks.
- **Client portal:** ownership-scoped summaries, cases, hearings, appointments,
  shared documents, and invoices.
- **Localization:** English/Bangla content fields and language negotiation.

## Technology

| Component | Implementation |
|---|---|
| Runtime | Python 3.12 |
| Web framework | Django 5.2 |
| API | Django REST Framework |
| Authentication | Simple JWT; Django sessions for Admin |
| Local database | MySQL 8.4 |
| Optional hosted database | PostgreSQL via `DATABASE_URL` |
| Application server | Waitress |
| Hosted static assets | WhiteNoise in the Render profile |
| Configuration | Environment variables / python-decouple |
| Cross-origin access | django-cors-headers |

Dependency versions are pinned in `requirements-common.txt`. `requirements.txt`
adds the MySQL driver; `requirements-production.txt` adds Waitress;
`requirements-render.txt` selects PostgreSQL, Waitress, and WhiteNoise.

## Repository structure

```text
law-firm-backend/
├── accounts/           # User model, authentication, roles, integration tests
├── academy/            # Pathways, courses, sessions, registrations, portal APIs
├── billing/            # Invoices and payment records
├── cases/              # Cases, assignments, notes, hearings, tasks
├── clients/            # Client records and access controls
├── config/             # Settings profiles, root URLs, WSGI/ASGI entry points
├── documents/          # Private document storage and download endpoints
├── firm/               # Firm content, lawyer profiles, branding
├── intake/             # Consultation requests and appointments
├── knowledge/          # Articles, FAQs, search, guided help, support contacts
├── legalaid/           # Legal-aid applications and tracking
├── deploy/             # Deployment environment and nginx templates
├── docs/               # API reference, permission matrix, deployment guide
├── scripts/            # Documentation generators and application launch helpers
├── manage.py           # Django management entry point
├── render.yaml         # Optional Render demonstration configuration
└── requirements*.txt   # Pinned installation profiles
```

Applications contain their own models, API views, serializers, URL configuration,
Admin configuration, migrations, and tests as applicable. Business records are
stored through Django's ORM. Private documents are stored separately from public
branding assets.

## Local installation

### Prerequisites

- Python 3.12 and Git.
- A running MySQL 8.4 server.
- Authorised access to the backend repository.
- A separate local database and credentials for each development environment.

The following commands use PowerShell. On Linux/macOS, use `.venv/bin/python`
instead of `.venv\Scripts\python.exe` and install the platform's MySQL client
development libraries if required by `mysqlclient`.

### 1. Clone and install dependencies

```powershell
git clone https://github.com/Cyber-Bit-Byte/law-firm-backend.git
Set-Location law-firm-backend
git switch main
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

For an existing checkout, save local changes before pulling updates. Virtual
environments, database contents, credentials, and uploads are not distributed
through Git.

### 2. Create the database

Run the following using a local MySQL administrator. Replace the password
placeholder before execution and keep credentials out of source control.

```sql
CREATE DATABASE lawfirm_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'lawfirm_user'@'localhost' IDENTIFIED BY 'REPLACE_WITH_A_UNIQUE_PASSWORD';
GRANT ALL PRIVILEGES ON lawfirm_db.* TO 'lawfirm_user'@'localhost';
GRANT ALL PRIVILEGES ON `test\_lawfirm\_db`.* TO 'lawfirm_user'@'localhost';
```

The final grant is for the disposable local test database only. Do not grant
test-database privileges to a production application account. If a database or
user already exists, review its configuration rather than recreating it.

### 3. Configure the environment

Copy the template only when `.env` does not already exist:

```powershell
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
```

Store the generated value as `SECRET_KEY` in `.env` and configure the database.

| Variable | Purpose / local value |
|---|---|
| `SECRET_KEY` | Independently generated application secret |
| `DEBUG` | `True` for local development only |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` |
| `DB_NAME` | `lawfirm_db` |
| `DB_USER` | `lawfirm_user` |
| `DB_PASSWORD` | Password of the local database account |
| `DB_HOST` | `127.0.0.1` |
| `DB_PORT` | Actual MySQL port; normally `3306` |
| `CORS_ALLOWED_ORIGINS` | Exact frontend origins, separated by commas |
| `DATABASE_URL` | Optional PostgreSQL URL; overrides the MySQL configuration |

Leave `DATABASE_URL` unset when using MySQL. Never commit `.env` or disclose
connection URLs, passwords, tokens, or application secrets.

### 4. Apply migrations and create an administrator

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
```

There are no default administrator credentials. Use the account created for the
current environment. Passwords can be reset locally with
`manage.py changepassword <username>`.

### 5. Start the development server

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

- Administration: http://127.0.0.1:8000/admin/
- Public API example: http://127.0.0.1:8000/api/courses/
- The root path `/` has no application homepage and returns 404.

`runserver` is intended for local development. Deployment settings and WSGI
startup are documented in [Deployment](docs/DEPLOYMENT_RENDER.md).

### Optional development data

```powershell
.\.venv\Scripts\python.exe manage.py seed_demo --created-by YOUR_ADMIN_USERNAME
```

The command creates linked fictional records across the applications. It requires
an active admin-role account and either local `DEBUG=True` or the explicit hosted
demonstration profile. Repeated runs preserve existing records, passwords, and
dates. Sample users have unusable passwords until explicitly configured. Knowledge
samples remain unpublished pending review; no verified support numbers are invented.

## API and frontend integration

See the [API reference](docs/API_REFERENCE.md) for all routes, methods, request
examples, response shapes, filters, and permissions. The
[permission matrix](docs/PERMISSIONS.md) documents role-level access and object scope.

| Endpoint | Purpose |
|---|---|
| `POST /api/auth/token/` | Obtain access and refresh tokens |
| `POST /api/auth/token/refresh/` | Refresh an access token |
| `GET /api/auth/me/` | Retrieve the authenticated user's identity and role |
| `GET /api/practice-areas/` | Public practice-area listing |
| `GET /api/courses/` | Public Academy course listing |
| `GET /api/portal/summary/` | Client-only account summary |

- Set the frontend API base URL to the backend origin, locally
  `http://127.0.0.1:8000`. Each developer runs their own local backend.
- Serve frontend files over HTTP rather than `file://`. Add its exact origin to
  `CORS_ALLOWED_ORIGINS` and restart Django after configuration changes.
- Send JSON requests with `Content-Type: application/json`. Protected endpoints
  require `Authorization: Bearer <access_token>`; Admin cookies do not authenticate APIs.
- Access tokens expire after 30 minutes; refresh tokens expire after one day.
  Keep tokens out of URLs and logs. Server-side token revocation is not implemented.
- Send `Accept-Language: en` or `bn`. Translate frontend labels separately;
  not all custom validation messages are translated.
- Lists use `{count, next, previous, results}` with a default page size of 20.
- Handle 400, 401, 403, 404, and 429 explicitly. A 204 response has no JSON body.
- Upload documents using `FormData`; let the browser set the multipart boundary.
  Download protected files with the bearer header and process the binary response.
- Use returned record IDs, ISO 8601 datetimes with offsets, and decimal strings
  for monetary values. Do not expose private storage paths as public links.
- Client portal endpoints require a client-role token. An admin token does not
  substitute for a client login.

## Verification

With the local database running:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py migrate --check
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/api_reference.py --check
.\.venv\Scripts\python.exe manage.py test accounts clients firm intake cases knowledge documents billing legalaid academy --noinput
```

The test suite covers validation, roles and ownership, private documents,
appointment conflicts, billing balances, registration capacity, repeatable seeds,
deployment settings, and an API-only intake-to-client-portal workflow. Its access
matrix exercises 105 canonical route/method combinations across five roles.
Tests create and remove a separate test database. Never run them against a shared
or production database account. Passing tests establish the checked behaviour;
they are not a guarantee that every possible defect has been excluded.

Regenerate technical reference documents after changing the API contract:

```powershell
.\.venv\Scripts\python.exe scripts/api_reference.py
.\.venv\Scripts\python.exe scripts/permission_matrix.py
```

Review the generated diff alongside the implementation and its tests.

## Deployment and operational scope

`config.settings` supports local development. `config.production` provides
explicit HTTPS settings, secure cookies, allowed hosts/origins, a shared database
cache, and configurable storage directories. `config.render` and `render.yaml`
provide an optional temporary demonstration deployment with PostgreSQL.

See [Deployment](docs/DEPLOYMENT_RENDER.md) for configuration, startup, backup,
restoration, and hosting limitations. Deployment templates do not establish that
a public service is provisioned or operational.

- Case files require protected, durable storage and backups separate from database backups.
- Upload size/format validation is implemented; malware scanning is not.
- Billing records payments; it does not process online payments.
- Guided help uses structured content, not an AI legal-advice service.
- Academy provides listings and registrations, not examinations or certification.
- Legal content and support contacts require authorised review before publication.
- Production release requires infrastructure configuration, monitoring, restoration
  verification, and frontend acceptance testing for the target environment.

## Development workflow

Use feature branches and pull requests for changes. `develop` is the integration
branch and `main` is the release branch. Follow repository protection and review
requirements. Include migrations when models change, update relevant tests/API
documentation, and exclude secrets, local databases, generated environments, and
uploaded files from commits.

After pulling an update, install the appropriate requirements, apply migrations,
and restart the application. Preserve the environment's existing `.env`.
