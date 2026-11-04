# Anadi Law Firm — Full-stack project

```
anadi-law-firm/
├── backend/    Django REST API (your original backend + small additions)
└── frontend/   React + Vite website, firm dashboard and client portal
```

## Quick start (local, 2 terminals)

### 1. Backend — terminal 1

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate      Linux/macOS:  source .venv/bin/activate
pip install -r requirements-common.txt          # SQLite mode (no MySQL needed)
# (or: pip install -r requirements.txt  for MySQL)
```

Create `backend/.env`:

```env
SECRET_KEY=paste-a-long-random-string-here
DEBUG=True
USE_SQLITE=True
ALLOWED_HOSTS=127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

> Using MySQL instead? Remove `USE_SQLITE` and add `DB_NAME / DB_USER / DB_PASSWORD / DB_HOST / DB_PORT` as in `backend/README.md`.

```bash
python manage.py migrate
python manage.py seed_local_showcase --password "Anadi-Local-2026!"
python manage.py runserver 127.0.0.1:8000
```

`seed_local_showcase` (DEBUG only) creates demo data and these logins, all with the password you pass:

| Username | Role | Goes to |
|---|---|---|
| `admin` | Admin | `/dashboard` (everything + User accounts) |
| `stage3_demo_staff` | Staff | `/dashboard` |
| `stage3_demo_lawyer` | Lawyer | `/dashboard` (only assigned cases) |
| `stage3_demo_client_one` | Client | `/portal` |

### 2. Frontend — terminal 2

```bash
cd frontend
npm install
cp .env.example .env        # VITE_API_BASE_URL=http://127.0.0.1:8000
npm run dev                 # http://127.0.0.1:5173
```

Production build: `npm run build` → static files in `frontend/dist/` (deploy to Vercel/Netlify; set `VITE_API_BASE_URL` to the hosted API and add the site origin to the backend `CORS_ALLOWED_ORIGINS`). For client-side routing on Vercel add a rewrite of all paths to `/index.html`.

## What the frontend covers

**Public website** (EN / বাংলা toggle, sends `Accept-Language`)
Home · Practice areas + detail · Lawyers + profile · Book consultation · Legal-aid application + private tracking · Knowledge hub (articles, FAQs, rights topics, search) · Guided help flow · Academy (courses, live sessions, registration) · Contact (firm profile + verified help lines) · Login

**Firm dashboard** (admin / staff / lawyer — role-aware)
Overview (hearings, my tasks, appointments, new requests, outstanding balance) · Consultations (status, convert → client) · Legal aid (review, match → client + case) · Clients (create/edit, link portal login) · Cases (filters/search, create, detail page with Notes [internal/shared], Team assignments, Hearings, Tasks, Documents upload/download, Appointments, Invoices + payments) · Hearings · Appointments · Tasks (all / my) · Documents · Invoices · Payments · User accounts (admin) · Change password

**Client portal**
Overview · My cases with shared updates · Hearings · Appointments · Shared documents (download) · Invoices · Change password

Design: palette taken from the logo — forest `#4C5840`, sage `#7E986C`, cream `#F6F1E4`, with a brass accent `#B08D57`; Cormorant Garamond headings (matches the ANADI serif wordmark), Manrope / Hind Siliguri body text.

## Backend changes made for the frontend

All original tests still pass, plus new ones (`accounts/test_users.py`). API docs regenerated (`docs/API_REFERENCE.md`, `docs/PERMISSIONS.md` — now 110 routes).

- `GET/POST /api/users/`, `GET/PATCH /api/users/<id>/` — firm members list active users (needed to pick lawyers / assignees / portal logins); **only admin** creates or edits accounts (password validated, can't deactivate yourself). Filters: `role`, `search`, `without_client=1`.
- `Client.assigned_lawyer` (migration `clients/0002`) — the ERD's USER *manages* CLIENT relation; editable in dashboard + Django Admin, filter `?assigned_lawyer=`, client sees their lawyer's name in the portal.
- `POST /api/auth/change-password/` — any logged-in user.
- Filters: appointments `client, case, lawyer, status` (firm roles); invoices `case`; consultations & legal-aid `status`.
- `CORS_EXPOSE_HEADERS = ['Content-Disposition']` so document downloads keep their filename.
- `USE_SQLITE=True` option for zero-setup local development.
- `seed_local_showcase` command (DEBUG only) for demo logins + published sample knowledge.

Note: the frontend keeps JWTs in `localStorage` (simple for this project). For a real production deployment consider httpOnly-cookie auth.

## Where each thing is managed

| Task | React dashboard | Django Admin (`/admin/`) |
|---|---|---|
| Clients, cases, team, notes, hearings, tasks, documents, appointments, invoices, payments, consultations, legal aid | ✅ | ✅ |
| User accounts (create, role, activate/deactivate, reset password) | ✅ admin only | ✅ |
| Firm profile, practice areas, lawyer public profiles, knowledge articles/FAQs review & publish, help contacts, guided flows, Academy courses/sessions | — | ✅ (content management) |
