# Complete backend API reference

Generated with `python scripts/api_reference.py`; use `--check` to detect drift.

## Conventions

- Base URL locally: `http://127.0.0.1:8000`. This is not a hosted production URL.
- JSON bodies use `Content-Type: application/json`. Private APIs require `Authorization: Bearer <access-token>`.
- Send `Accept-Language: en` or `bn` for bilingual fields; missing translations fall back to English.
- Lists use `{count, next, previous, results}` and page size 20; use `?page=2`.
- Examples below are fictional response excerpts. IDs are illustrative: obtain actual IDs from list/create responses.
- Date examples are illustrative; time-sensitive operations require valid future dates. Datetimes accept ISO 8601 offsets.
- Server-controlled IDs, ownership actors and timestamps are read-only. Client-role serializers omit internal fields.
- PATCH changes supplied fields; PUT supplies the writable required fields shown in its example. Ownership cannot be transferred.
- POST creation normally returns 201; update/read returns 200; DELETE returns 204 with no body.
- Validation errors use field-to-message-list objects, e.g. `{"amount":["Payment exceeds the remaining invoice balance."]}`.
- General errors use `{"detail":"..."}`. Handle 400 (invalid), 401 (login), 403 (role), 404 (missing/inaccessible), 405 (unsupported method), 429 (rate limit).
- Do not depend on exact English error text. Custom messages are not all translated to Bangla.
- Login/refresh share 20 requests/min/IP. Consultation forms: 5/min and 30/day. Legal-aid/Academy forms share 5/min and 30/day. Tracking: 100/hour.
- Browser Admin cookies do not authenticate JWT APIs. No public account-signup endpoint exists.
- All three firm roles can manage clients, appointments, consultations, invoices/payments and legal-aid records. Case resources are assignment-scoped for lawyers.
- Client reads are ownership-scoped; notes must be shared, documents must be client-visible. Portal accepts client-role tokens only.
- The `/api/` router landing response is not a complete endpoint index. Use this document for all modules.

## Filters and special behaviour

- Cases: `client`, `practice_area`, `status`, `lawyer`, `search`, `ordering`; ordering supports created_at, updated_at, filing_date and case_number (prefix `-` for descending).
- Assignments, notes, hearings, tasks and documents: `case=<id>`. Invoices: `client=<id>`, `case=<id>`. Payments: `invoice=<id>`. Appointments (firm roles): `client`, `case`, `lawyer`, `status`. Consultations and legal-aid applications: `status`. Users: `role` (comma-separated), `search`, `without_client=1`. Clients (firm roles): `assigned_lawyer`, `status`, `search`.
- Articles/FAQs/search: `jurisdiction=<code>`, `topic=<slug>`, `language=en|bn`. Search requires `q` (1–200 characters).
- Courses: `pathway=<id>`. Live sessions: `course=<id>`. Only future published sessions with available parent content are listed.
- Jurisdiction detail uses code; practice areas/topics/articles/pathways use slug; other detail routes use numeric ID.
- Only reviewed/published knowledge and verified help contacts are public. Seeds leave legal content as drafts.
- Conversion actions are idempotent: repeat returns 200 with `created:false` and the existing linked IDs.
- Assignments accept `user` and role lead/support. Legacy `lawyer` is supported for lawyers only; never send both.
- Cases support court, opposite_party, priority low/normal/high and closed_date. Closed dates require closed/archived status and cannot precede filing.
- Notes and assignments cannot be edited through the API. Correct a note with a new note; change an assignment by removing/recreating it.
- Documents: POST multipart/form-data with the named fields and a real file part. Allowed PDF/PNG/JPEG/UTF-8 TXT, nonempty, maximum 10 MB. File and case are immutable.
- Document PATCH/PUT edits metadata only. Download is binary with attachment, nosniff and no-store headers; storage paths are never public.
- Invoices use BDT and derive paid/partial/unpaid status from payments. Payments cannot exceed the balance; invoices with payments cannot be deleted.
- Public form `website` is an optional honeypot: omit or leave blank. Legal-aid answers allow at most 20 short scalar values, 5000 total JSON characters.
- Tracking codes are confidential receipt identifiers. Public tracking returns status only, with no-store headers.
- Session registration normalizes email, rejects duplicates and full/closed sessions. There is no public participant-list endpoint.
- Guided flow: read start, show question/options, follow next_question when present; otherwise GET the selected option result. Results are indicative, not eligibility decisions.

## Endpoint index

All **110 canonical route/method combinations** are listed. HEAD/OPTIONS and format suffixes are protocol aliases.

| Method | Route | Who may call | Example |
|---|---|---|---|
| GET | `/api/` | client, staff, lawyer, admin | [Example 1](#example-1) |
| GET | `/api/appointments/` | client, staff, lawyer, admin | [Example 2](#example-2) |
| POST | `/api/appointments/` | staff, lawyer, admin | [Example 3](#example-3) |
| DELETE | `/api/appointments/<pk>/` | staff, lawyer, admin | [Example 4](#example-4) |
| GET | `/api/appointments/<pk>/` | client, staff, lawyer, admin | [Example 5](#example-5) |
| PATCH | `/api/appointments/<pk>/` | staff, lawyer, admin | [Example 6](#example-6) |
| PUT | `/api/appointments/<pk>/` | staff, lawyer, admin | [Example 7](#example-7) |
| GET | `/api/articles/` | Public | [Example 8](#example-8) |
| GET | `/api/articles/<slug>/` | Public | [Example 9](#example-9) |
| POST | `/api/auth/change-password/` | client, staff, lawyer, admin | [Example 10](#example-10) |
| GET | `/api/auth/me/` | client, staff, lawyer, admin | [Example 11](#example-11) |
| POST | `/api/auth/token/` | Public | [Example 12](#example-12) |
| POST | `/api/auth/token/refresh/` | Public | [Example 13](#example-13) |
| GET | `/api/case-assignments/` | staff, lawyer, admin | [Example 14](#example-14) |
| POST | `/api/case-assignments/` | staff, admin | [Example 15](#example-15) |
| DELETE | `/api/case-assignments/<pk>/` | staff, admin | [Example 16](#example-16) |
| GET | `/api/case-assignments/<pk>/` | staff, lawyer, admin | [Example 17](#example-17) |
| GET | `/api/case-notes/` | client, staff, lawyer, admin | [Example 18](#example-18) |
| POST | `/api/case-notes/` | staff, lawyer, admin | [Example 19](#example-19) |
| GET | `/api/case-notes/<pk>/` | client, staff, lawyer, admin | [Example 20](#example-20) |
| GET | `/api/cases/` | client, staff, lawyer, admin | [Example 21](#example-21) |
| POST | `/api/cases/` | staff, admin | [Example 22](#example-22) |
| GET | `/api/cases/<pk>/` | client, staff, lawyer, admin | [Example 23](#example-23) |
| PATCH | `/api/cases/<pk>/` | staff, lawyer, admin | [Example 24](#example-24) |
| PUT | `/api/cases/<pk>/` | staff, lawyer, admin | [Example 25](#example-25) |
| GET | `/api/clients/` | client, staff, lawyer, admin | [Example 26](#example-26) |
| POST | `/api/clients/` | staff, lawyer, admin | [Example 27](#example-27) |
| GET | `/api/clients/<pk>/` | client, staff, lawyer, admin | [Example 28](#example-28) |
| PATCH | `/api/clients/<pk>/` | staff, lawyer, admin | [Example 29](#example-29) |
| PUT | `/api/clients/<pk>/` | staff, lawyer, admin | [Example 30](#example-30) |
| GET | `/api/consultations/` | staff, lawyer, admin | [Example 31](#example-31) |
| POST | `/api/consultations/` | Public | [Example 32](#example-32) |
| GET | `/api/consultations/<pk>/` | staff, lawyer, admin | [Example 33](#example-33) |
| PATCH | `/api/consultations/<pk>/` | staff, lawyer, admin | [Example 34](#example-34) |
| PUT | `/api/consultations/<pk>/` | staff, lawyer, admin | [Example 35](#example-35) |
| POST | `/api/consultations/<pk>/convert/` | staff, lawyer, admin | [Example 36](#example-36) |
| GET | `/api/courses/` | Public | [Example 37](#example-37) |
| GET | `/api/courses/<pk>/` | Public | [Example 38](#example-38) |
| GET | `/api/documents/` | client, staff, lawyer, admin | [Example 39](#example-39) |
| POST | `/api/documents/` | staff, lawyer, admin | [Example 40](#example-40) |
| GET | `/api/documents/<pk>/` | client, staff, lawyer, admin | [Example 41](#example-41) |
| PATCH | `/api/documents/<pk>/` | staff, lawyer, admin | [Example 42](#example-42) |
| PUT | `/api/documents/<pk>/` | staff, lawyer, admin | [Example 43](#example-43) |
| GET | `/api/documents/<pk>/download/` | client, staff, lawyer, admin | [Example 44](#example-44) |
| GET | `/api/faqs/` | Public | [Example 45](#example-45) |
| GET | `/api/faqs/<pk>/` | Public | [Example 46](#example-46) |
| GET | `/api/firm/profile/` | Public | [Example 47](#example-47) |
| GET | `/api/guided-flows/` | Public | [Example 48](#example-48) |
| GET | `/api/guided-flows/<pk>/` | Public | [Example 49](#example-49) |
| GET | `/api/guided-flows/<pk>/start/` | Public | [Example 50](#example-50) |
| GET | `/api/guided-options/<pk>/result/` | Public | [Example 51](#example-51) |
| GET | `/api/guided-questions/<pk>/` | Public | [Example 52](#example-52) |
| GET | `/api/hearings/` | client, staff, lawyer, admin | [Example 53](#example-53) |
| POST | `/api/hearings/` | staff, lawyer, admin | [Example 54](#example-54) |
| DELETE | `/api/hearings/<pk>/` | staff, lawyer, admin | [Example 55](#example-55) |
| GET | `/api/hearings/<pk>/` | client, staff, lawyer, admin | [Example 56](#example-56) |
| PATCH | `/api/hearings/<pk>/` | staff, lawyer, admin | [Example 57](#example-57) |
| PUT | `/api/hearings/<pk>/` | staff, lawyer, admin | [Example 58](#example-58) |
| GET | `/api/hearings/upcoming/` | client, staff, lawyer, admin | [Example 59](#example-59) |
| GET | `/api/help-contacts/` | Public | [Example 60](#example-60) |
| GET | `/api/invoices/` | client, staff, lawyer, admin | [Example 61](#example-61) |
| POST | `/api/invoices/` | staff, lawyer, admin | [Example 62](#example-62) |
| DELETE | `/api/invoices/<pk>/` | staff, lawyer, admin | [Example 63](#example-63) |
| GET | `/api/invoices/<pk>/` | client, staff, lawyer, admin | [Example 64](#example-64) |
| PATCH | `/api/invoices/<pk>/` | staff, lawyer, admin | [Example 65](#example-65) |
| PUT | `/api/invoices/<pk>/` | staff, lawyer, admin | [Example 66](#example-66) |
| GET | `/api/jurisdictions/` | Public | [Example 67](#example-67) |
| GET | `/api/jurisdictions/<code>/` | Public | [Example 68](#example-68) |
| GET | `/api/knowledge/search/` | Public | [Example 69](#example-69) |
| GET | `/api/lawyers/` | Public | [Example 70](#example-70) |
| GET | `/api/lawyers/<pk>/` | Public | [Example 71](#example-71) |
| GET | `/api/legal-aid/applications/` | staff, lawyer, admin | [Example 72](#example-72) |
| GET | `/api/legal-aid/applications/<pk>/` | staff, lawyer, admin | [Example 73](#example-73) |
| PATCH | `/api/legal-aid/applications/<pk>/` | staff, lawyer, admin | [Example 74](#example-74) |
| PUT | `/api/legal-aid/applications/<pk>/` | staff, lawyer, admin | [Example 75](#example-75) |
| POST | `/api/legal-aid/applications/<pk>/convert/` | staff, lawyer, admin | [Example 76](#example-76) |
| POST | `/api/legal-aid/apply/` | Public | [Example 77](#example-77) |
| GET | `/api/legal-aid/track/<code>/` | Public | [Example 78](#example-78) |
| GET | `/api/live-sessions/` | Public | [Example 79](#example-79) |
| GET | `/api/live-sessions/<pk>/` | Public | [Example 80](#example-80) |
| GET | `/api/pathways/` | Public | [Example 81](#example-81) |
| GET | `/api/pathways/<slug>/` | Public | [Example 82](#example-82) |
| GET | `/api/payments/` | staff, lawyer, admin | [Example 83](#example-83) |
| POST | `/api/payments/` | staff, lawyer, admin | [Example 84](#example-84) |
| DELETE | `/api/payments/<pk>/` | staff, lawyer, admin | [Example 85](#example-85) |
| GET | `/api/payments/<pk>/` | staff, lawyer, admin | [Example 86](#example-86) |
| PATCH | `/api/payments/<pk>/` | staff, lawyer, admin | [Example 87](#example-87) |
| PUT | `/api/payments/<pk>/` | staff, lawyer, admin | [Example 88](#example-88) |
| GET | `/api/portal/appointments/` | client | [Example 89](#example-89) |
| GET | `/api/portal/cases/` | client | [Example 90](#example-90) |
| GET | `/api/portal/documents/` | client | [Example 91](#example-91) |
| GET | `/api/portal/hearings/` | client | [Example 92](#example-92) |
| GET | `/api/portal/invoices/` | client | [Example 93](#example-93) |
| GET | `/api/portal/summary/` | client | [Example 94](#example-94) |
| GET | `/api/practice-areas/` | Public | [Example 95](#example-95) |
| GET | `/api/practice-areas/<slug>/` | Public | [Example 96](#example-96) |
| GET | `/api/rights-topics/` | Public | [Example 97](#example-97) |
| GET | `/api/rights-topics/<slug>/` | Public | [Example 98](#example-98) |
| POST | `/api/session-registrations/` | Public | [Example 99](#example-99) |
| GET | `/api/tasks/` | staff, lawyer, admin | [Example 100](#example-100) |
| POST | `/api/tasks/` | staff, lawyer, admin | [Example 101](#example-101) |
| DELETE | `/api/tasks/<pk>/` | staff, lawyer, admin | [Example 102](#example-102) |
| GET | `/api/tasks/<pk>/` | staff, lawyer, admin | [Example 103](#example-103) |
| PATCH | `/api/tasks/<pk>/` | staff, lawyer, admin | [Example 104](#example-104) |
| PUT | `/api/tasks/<pk>/` | staff, lawyer, admin | [Example 105](#example-105) |
| GET | `/api/tasks/my-tasks/` | staff, lawyer, admin | [Example 106](#example-106) |
| GET | `/api/users/` | staff, lawyer, admin | [Example 107](#example-107) |
| POST | `/api/users/` | admin | [Example 108](#example-108) |
| GET | `/api/users/<pk>/` | staff, lawyer, admin | [Example 109](#example-109) |
| PATCH | `/api/users/<pk>/` | admin | [Example 110](#example-110) |

## Example 1

`GET /api/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "pathways": "http://127.0.0.1:8000/api/pathways/"
}
```

## Example 2

`GET /api/appointments/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "client": 1,
      "lawyer": 2,
      "case": 1,
      "start": "2030-01-15T10:00:00+06:00",
      "end": "2030-01-15T11:00:00+06:00",
      "status": "scheduled"
    }
  ]
}
```

## Example 3

`POST /api/appointments/`

Request body (JSON):

```json
{
  "client": 1,
  "lawyer": 2,
  "case": 1,
  "start": "2030-01-15T10:00:00+06:00",
  "end": "2030-01-15T11:00:00+06:00",
  "appointment_type": "consultation"
}
```

Response: **201** (representative excerpt).

```json
{
  "id": 1,
  "client": 1,
  "lawyer": 2,
  "case": 1,
  "start": "2030-01-15T10:00:00+06:00",
  "end": "2030-01-15T11:00:00+06:00",
  "status": "scheduled"
}
```

## Example 4

`DELETE /api/appointments/1/`

Request body: none.

Response: **204** (no response body).

## Example 5

`GET /api/appointments/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "client": 1,
  "lawyer": 2,
  "case": 1,
  "start": "2030-01-15T10:00:00+06:00",
  "end": "2030-01-15T11:00:00+06:00",
  "status": "scheduled"
}
```

## Example 6

`PATCH /api/appointments/1/`

Request body (JSON):

```json
{
  "status": "cancelled"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "client": 1,
  "lawyer": 2,
  "case": 1,
  "start": "2030-01-15T10:00:00+06:00",
  "end": "2030-01-15T11:00:00+06:00",
  "status": "cancelled"
}
```

## Example 7

`PUT /api/appointments/1/`

Request body (JSON):

```json
{
  "client": 1,
  "lawyer": 2,
  "case": 1,
  "start": "2030-01-15T10:00:00+06:00",
  "end": "2030-01-15T11:00:00+06:00",
  "appointment_type": "consultation"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "client": 1,
  "lawyer": 2,
  "case": 1,
  "start": "2030-01-15T10:00:00+06:00",
  "end": "2030-01-15T11:00:00+06:00",
  "status": "scheduled"
}
```

## Example 8

`GET /api/articles/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "slug": "sample-help-en",
      "title": "Sample: consultation information",
      "body": "Demonstration placeholder.",
      "language": "en",
      "is_sample": true,
      "disclaimer": "General information, not legal advice."
    }
  ]
}
```

## Example 9

`GET /api/articles/sample-help-en/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "slug": "sample-help-en",
  "title": "Sample: consultation information",
  "body": "Demonstration placeholder.",
  "language": "en",
  "is_sample": true,
  "disclaimer": "General information, not legal advice."
}
```

## Example 10

`POST /api/auth/change-password/`

Request body (JSON):

```json
{
  "current_password": "<current-password>",
  "new_password": "<new-password>"
}
```

Response: **200** (representative excerpt).

```json
{
  "detail": "Password changed."
}
```

## Example 11

`GET /api/auth/me/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "username": "sample_client",
  "role": "client"
}
```

## Example 12

`POST /api/auth/token/`

Request body (JSON):

```json
{
  "username": "<your-username>",
  "password": "<your-password>"
}
```

Response: **200** (representative excerpt).

```json
{
  "access": "<access-token>",
  "refresh": "<refresh-token>"
}
```

## Example 13

`POST /api/auth/token/refresh/`

Request body (JSON):

```json
{
  "refresh": "<refresh-token>"
}
```

Response: **200** (representative excerpt).

```json
{
  "access": "<access-token>"
}
```

## Example 14

`GET /api/case-assignments/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "case": 1,
      "user": 2,
      "lawyer": 2,
      "role": "lead"
    }
  ]
}
```

## Example 15

`POST /api/case-assignments/`

Request body (JSON):

```json
{
  "case": 1,
  "user": 2,
  "role": "lead"
}
```

Response: **201** (representative excerpt).

```json
{
  "id": 1,
  "case": 1,
  "user": 2,
  "lawyer": 2,
  "role": "lead"
}
```

## Example 16

`DELETE /api/case-assignments/1/`

Request body: none.

Response: **204** (no response body).

## Example 17

`GET /api/case-assignments/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "case": 1,
  "user": 2,
  "lawyer": 2,
  "role": "lead"
}
```

## Example 18

`GET /api/case-notes/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "case": 1,
      "body": "Sample shared update",
      "is_internal": false
    }
  ]
}
```

## Example 19

`POST /api/case-notes/`

Request body (JSON):

```json
{
  "case": 1,
  "body": "Sample shared update",
  "is_internal": false
}
```

Response: **201** (representative excerpt).

```json
{
  "id": 1,
  "case": 1,
  "body": "Sample shared update",
  "is_internal": false
}
```

## Example 20

`GET /api/case-notes/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "case": 1,
  "body": "Sample shared update",
  "is_internal": false
}
```

## Example 21

`GET /api/cases/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "case_number": "SAMPLE-001",
      "title": "Sample case",
      "status": "open",
      "court": "Sample court",
      "lead_lawyers": []
    }
  ]
}
```

## Example 22

`POST /api/cases/`

Request body (JSON):

```json
{
  "case_number": "SAMPLE-001",
  "title": "Sample case",
  "client": 1,
  "practice_area": 1,
  "court": "Sample court",
  "priority": "normal"
}
```

Response: **201** (representative excerpt).

```json
{
  "id": 1,
  "case_number": "SAMPLE-001",
  "title": "Sample case",
  "status": "open",
  "court": "Sample court",
  "lead_lawyers": []
}
```

## Example 23

`GET /api/cases/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "case_number": "SAMPLE-001",
  "title": "Sample case",
  "status": "open",
  "court": "Sample court",
  "lead_lawyers": []
}
```

## Example 24

`PATCH /api/cases/1/`

Request body (JSON):

```json
{
  "title": "Updated sample title"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "case_number": "SAMPLE-001",
  "title": "Updated sample title",
  "status": "open",
  "court": "Sample court",
  "lead_lawyers": []
}
```

## Example 25

`PUT /api/cases/1/`

Request body (JSON):

```json
{
  "case_number": "SAMPLE-001",
  "title": "Sample case",
  "client": 1,
  "practice_area": 1,
  "court": "Sample court",
  "priority": "normal"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "case_number": "SAMPLE-001",
  "title": "Sample case",
  "status": "open",
  "court": "Sample court",
  "lead_lawyers": []
}
```

## Example 26

`GET /api/clients/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "full_name": "Sample Client",
      "status": "active"
    }
  ]
}
```

## Example 27

`POST /api/clients/`

Request body (JSON):

```json
{
  "full_name": "Sample Client",
  "user": 3,
  "status": "active"
}
```

Response: **201** (representative excerpt).

```json
{
  "id": 1,
  "full_name": "Sample Client",
  "status": "active"
}
```

## Example 28

`GET /api/clients/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "full_name": "Sample Client",
  "status": "active"
}
```

## Example 29

`PATCH /api/clients/1/`

Request body (JSON):

```json
{
  "full_name": "Updated sample name"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "full_name": "Updated sample name",
  "status": "active"
}
```

## Example 30

`PUT /api/clients/1/`

Request body (JSON):

```json
{
  "full_name": "Sample Client",
  "user": 3,
  "status": "active"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "full_name": "Sample Client",
  "status": "active"
}
```

## Example 31

`GET /api/consultations/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Sample Visitor",
      "status": "new",
      "client": null
    }
  ]
}
```

## Example 32

`POST /api/consultations/`

Request body (JSON):

```json
{
  "name": "Sample Visitor",
  "phone": "DEMO-NOT-A-PHONE",
  "practice_area": 1,
  "message": "Fictional request",
  "preferred_language": "en"
}
```

Response: **201** (representative excerpt).

```json
{
  "id": 1,
  "status": "new"
}
```

## Example 33

`GET /api/consultations/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "name": "Sample Visitor",
  "status": "new",
  "client": null
}
```

## Example 34

`PATCH /api/consultations/1/`

Request body (JSON):

```json
{
  "status": "contacted"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "name": "Sample Visitor",
  "status": "contacted",
  "client": null
}
```

## Example 35

`PUT /api/consultations/1/`

Request body (JSON):

```json
{
  "status": "contacted"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "name": "Sample Visitor",
  "status": "contacted",
  "client": null
}
```

## Example 36

`POST /api/consultations/1/convert/`

Request body (JSON):

```json
{}
```

Response: **201** (representative excerpt).

```json
{
  "consultation_id": 1,
  "client_id": 1,
  "status": "converted",
  "created": true
}
```

## Example 37

`GET /api/courses/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "pathway": 1,
      "title": "Sample: finding support",
      "level": "beginner",
      "duration": "1 hour",
      "is_sample": true
    }
  ]
}
```

## Example 38

`GET /api/courses/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "pathway": 1,
  "title": "Sample: finding support",
  "level": "beginner",
  "duration": "1 hour",
  "is_sample": true
}
```

## Example 39

`GET /api/documents/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "case": 1,
      "title": "Sample document",
      "version": 1,
      "download_url": "/api/documents/1/download/"
    }
  ]
}
```

## Example 40

`POST /api/documents/`

Request body (multipart fields; file is a binary part):

```json
{
  "case": 1,
  "title": "Sample document",
  "document_type": "sample",
  "version": 1,
  "file": "<binary sample.txt>"
}
```

Response: **201** (representative excerpt).

```json
{
  "id": 1,
  "case": 1,
  "title": "Sample document",
  "version": 1,
  "download_url": "/api/documents/1/download/"
}
```

## Example 41

`GET /api/documents/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "case": 1,
  "title": "Sample document",
  "version": 1,
  "download_url": "/api/documents/1/download/"
}
```

## Example 42

`PATCH /api/documents/1/`

Request body (JSON):

```json
{
  "case": 1,
  "title": "Sample document",
  "document_type": "sample",
  "version": 1
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "case": 1,
  "title": "Sample document",
  "version": 1,
  "download_url": "/api/documents/1/download/"
}
```

## Example 43

`PUT /api/documents/1/`

Request body (JSON):

```json
{
  "case": 1,
  "title": "Sample document",
  "document_type": "sample",
  "version": 1
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "case": 1,
  "title": "Sample document",
  "version": 1,
  "download_url": "/api/documents/1/download/"
}
```

## Example 44

`GET /api/documents/1/download/`

Request body: none.

Response: **200** (representative excerpt).

<binary file attachment; not JSON>

## Example 45

`GET /api/faqs/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "question": "Sample question",
      "answer": "Demonstration placeholder.",
      "language": "en",
      "disclaimer": "General information, not legal advice."
    }
  ]
}
```

## Example 46

`GET /api/faqs/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "question": "Sample question",
  "answer": "Demonstration placeholder.",
  "language": "en",
  "disclaimer": "General information, not legal advice."
}
```

## Example 47

`GET /api/firm/profile/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "name": "Anadi Law Firm",
  "tagline": "Sample website",
  "logo": "http://127.0.0.1:8000/static/firm/anadi-law-firm.png"
}
```

## Example 48

`GET /api/guided-flows/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Sample: finding help",
      "purpose": "issue_finder",
      "start_question": 1,
      "is_sample": true
    }
  ]
}
```

## Example 49

`GET /api/guided-flows/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "name": "Sample: finding help",
  "purpose": "issue_finder",
  "start_question": 1,
  "is_sample": true
}
```

## Example 50

`GET /api/guided-flows/1/start/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "flow": {
    "id": 1,
    "name": "Sample: finding help",
    "purpose": "issue_finder",
    "start_question": 1,
    "is_sample": true
  },
  "question": {
    "id": 1,
    "flow": 1,
    "text": "What would you like to discuss?",
    "order": 0,
    "options": [
      {
        "id": 1,
        "label": "Another matter",
        "next_question": null
      }
    ]
  },
  "indicative_only": true,
  "disclaimer": "General information, not legal advice."
}
```

## Example 51

`GET /api/guided-options/1/result/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "practice_area": null,
  "articles": [],
  "consultation_url": "/api/consultations/",
  "escalate_to_consultation": true,
  "indicative_only": true,
  "is_sample": true
}
```

## Example 52

`GET /api/guided-questions/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "flow": 1,
  "text": "What would you like to discuss?",
  "order": 0,
  "options": [
    {
      "id": 1,
      "label": "Another matter",
      "next_question": null
    }
  ]
}
```

## Example 53

`GET /api/hearings/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "case": 1,
      "court_name": "Sample court",
      "hearing_at": "2030-01-16T10:00:00+06:00"
    }
  ]
}
```

## Example 54

`POST /api/hearings/`

Request body (JSON):

```json
{
  "case": 1,
  "court_name": "Sample court",
  "hearing_at": "2030-01-16T10:00:00+06:00"
}
```

Response: **201** (representative excerpt).

```json
{
  "id": 1,
  "case": 1,
  "court_name": "Sample court",
  "hearing_at": "2030-01-16T10:00:00+06:00"
}
```

## Example 55

`DELETE /api/hearings/1/`

Request body: none.

Response: **204** (no response body).

## Example 56

`GET /api/hearings/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "case": 1,
  "court_name": "Sample court",
  "hearing_at": "2030-01-16T10:00:00+06:00"
}
```

## Example 57

`PATCH /api/hearings/1/`

Request body (JSON):

```json
{
  "court_name": "Updated sample court"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "case": 1,
  "court_name": "Updated sample court",
  "hearing_at": "2030-01-16T10:00:00+06:00"
}
```

## Example 58

`PUT /api/hearings/1/`

Request body (JSON):

```json
{
  "case": 1,
  "court_name": "Sample court",
  "hearing_at": "2030-01-16T10:00:00+06:00"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "case": 1,
  "court_name": "Sample court",
  "hearing_at": "2030-01-16T10:00:00+06:00"
}
```

## Example 59

`GET /api/hearings/upcoming/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "case": 1,
      "court_name": "Sample court",
      "hearing_at": "2030-01-16T10:00:00+06:00"
    }
  ]
}
```

## Example 60

`GET /api/help-contacts/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "label": "Example verified contact",
      "phone": "<verified-number>",
      "hours": "",
      "is_emergency": false
    }
  ]
}
```

## Example 61

`GET /api/invoices/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "invoice_number": "SAMPLE-INV-001",
      "amount": "100.00",
      "paid_amount": "40.00",
      "balance": "60.00",
      "status": "partial",
      "currency": "BDT"
    }
  ]
}
```

## Example 62

`POST /api/invoices/`

Request body (JSON):

```json
{
  "invoice_number": "SAMPLE-INV-001",
  "client": 1,
  "case": 1,
  "issue_date": "2030-01-15",
  "due_date": "2030-01-22",
  "amount": "100.00"
}
```

Response: **201** (representative excerpt).

```json
{
  "id": 1,
  "invoice_number": "SAMPLE-INV-001",
  "amount": "100.00",
  "paid_amount": "0.00",
  "balance": "100.00",
  "status": "unpaid",
  "currency": "BDT"
}
```

## Example 63

`DELETE /api/invoices/1/`

Request body: none.

Response: **204** (no response body).

## Example 64

`GET /api/invoices/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "invoice_number": "SAMPLE-INV-001",
  "amount": "100.00",
  "paid_amount": "40.00",
  "balance": "60.00",
  "status": "partial",
  "currency": "BDT"
}
```

## Example 65

`PATCH /api/invoices/1/`

Request body (JSON):

```json
{
  "amount": "50.00"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "invoice_number": "SAMPLE-INV-001",
  "amount": "50.00",
  "paid_amount": "40.00",
  "balance": "10.00",
  "status": "partial",
  "currency": "BDT"
}
```

## Example 66

`PUT /api/invoices/1/`

Request body (JSON):

```json
{
  "invoice_number": "SAMPLE-INV-001",
  "client": 1,
  "case": 1,
  "issue_date": "2030-01-15",
  "due_date": "2030-01-22",
  "amount": "100.00"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "invoice_number": "SAMPLE-INV-001",
  "amount": "100.00",
  "paid_amount": "40.00",
  "balance": "60.00",
  "status": "partial",
  "currency": "BDT"
}
```

## Example 67

`GET /api/jurisdictions/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "code": "bd",
      "name": "Bangladesh",
      "is_active": true
    }
  ]
}
```

## Example 68

`GET /api/jurisdictions/bd/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "code": "bd",
  "name": "Bangladesh",
  "is_active": true
}
```

## Example 69

`GET /api/knowledge/search/?q=sample`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "type": "article",
      "id": 1,
      "title": "Sample: consultation information",
      "language": "en"
    }
  ]
}
```

## Example 70

`GET /api/lawyers/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "full_name": "Sample Lawyer",
      "practice_areas": []
    }
  ]
}
```

## Example 71

`GET /api/lawyers/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "full_name": "Sample Lawyer",
  "practice_areas": []
}
```

## Example 72

`GET /api/legal-aid/applications/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "applicant_name": "Sample Applicant",
      "status": "submitted"
    }
  ]
}
```

## Example 73

`GET /api/legal-aid/applications/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "applicant_name": "Sample Applicant",
  "status": "submitted"
}
```

## Example 74

`PATCH /api/legal-aid/applications/1/`

Request body (JSON):

```json
{
  "status": "under_review"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "applicant_name": "Sample Applicant",
  "status": "under_review"
}
```

## Example 75

`PUT /api/legal-aid/applications/1/`

Request body (JSON):

```json
{
  "status": "under_review"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "applicant_name": "Sample Applicant",
  "status": "under_review"
}
```

## Example 76

`POST /api/legal-aid/applications/1/convert/`

Request body (JSON):

```json
{}
```

Response: **201** (representative excerpt).

```json
{
  "client": 1,
  "case": 1,
  "status": "matched",
  "created": true
}
```

## Example 77

`POST /api/legal-aid/apply/`

Request body (JSON):

```json
{
  "applicant_name": "Sample Applicant",
  "phone": "DEMO-NOT-A-PHONE",
  "practice_area": 1,
  "description": "Fictional request",
  "eligibility_answers": {
    "demo_only": true
  }
}
```

Response: **201** (representative excerpt).

```json
{
  "tracking_code": "<private-tracking-code>",
  "status": "submitted"
}
```

## Example 78

`GET /api/legal-aid/track/<your-private-tracking-code>/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "status": "submitted"
}
```

## Example 79

`GET /api/live-sessions/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Sample session",
      "start": "2030-01-15T10:00:00+06:00",
      "capacity": 10,
      "seats_remaining": 9,
      "is_sample": true
    }
  ]
}
```

## Example 80

`GET /api/live-sessions/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "title": "Sample session",
  "start": "2030-01-15T10:00:00+06:00",
  "capacity": 10,
  "seats_remaining": 9,
  "is_sample": true
}
```

## Example 81

`GET /api/pathways/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "slug": "sample-learning",
      "title": "Sample: learning pathway",
      "is_sample": true
    }
  ]
}
```

## Example 82

`GET /api/pathways/sample-learning/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "slug": "sample-learning",
  "title": "Sample: learning pathway",
  "is_sample": true
}
```

## Example 83

`GET /api/payments/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "invoice": 1,
      "amount": "40.00",
      "method": "cash",
      "date": "2030-01-15"
    }
  ]
}
```

## Example 84

`POST /api/payments/`

Request body (JSON):

```json
{
  "invoice": 1,
  "amount": "40.00",
  "method": "cash",
  "date": "2030-01-15"
}
```

Response: **201** (representative excerpt).

```json
{
  "id": 1,
  "invoice": 1,
  "amount": "40.00",
  "method": "cash",
  "date": "2030-01-15"
}
```

## Example 85

`DELETE /api/payments/1/`

Request body: none.

Response: **204** (no response body).

## Example 86

`GET /api/payments/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "invoice": 1,
  "amount": "40.00",
  "method": "cash",
  "date": "2030-01-15"
}
```

## Example 87

`PATCH /api/payments/1/`

Request body (JSON):

```json
{
  "amount": "50.00"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "invoice": 1,
  "amount": "50.00",
  "method": "cash",
  "date": "2030-01-15"
}
```

## Example 88

`PUT /api/payments/1/`

Request body (JSON):

```json
{
  "invoice": 1,
  "amount": "40.00",
  "method": "cash",
  "date": "2030-01-15"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "invoice": 1,
  "amount": "40.00",
  "method": "cash",
  "date": "2030-01-15"
}
```

## Example 89

`GET /api/portal/appointments/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "case": 1,
      "start": "2030-01-15T10:00:00+06:00",
      "end": "2030-01-15T11:00:00+06:00",
      "status": "scheduled",
      "lawyer_name": "Sample Lawyer"
    }
  ]
}
```

## Example 90

`GET /api/portal/cases/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "case_number": "SAMPLE-001",
      "title": "Sample case",
      "status": "open",
      "court": "Sample court",
      "lead_lawyers": []
    }
  ]
}
```

## Example 91

`GET /api/portal/documents/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "case": 1,
      "title": "Sample document",
      "version": 1,
      "download_url": "/api/documents/1/download/"
    }
  ]
}
```

## Example 92

`GET /api/portal/hearings/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "case": 1,
      "court_name": "Sample court",
      "hearing_at": "2030-01-16T10:00:00+06:00"
    }
  ]
}
```

## Example 93

`GET /api/portal/invoices/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "invoice_number": "SAMPLE-INV-001",
      "amount": "100.00",
      "paid_amount": "40.00",
      "balance": "60.00",
      "status": "partial",
      "currency": "BDT"
    }
  ]
}
```

## Example 94

`GET /api/portal/summary/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "cases": 1,
  "active_cases": 1,
  "upcoming_hearings": 1,
  "upcoming_appointments": 1,
  "documents": 0,
  "invoices": 1,
  "outstanding_balance": "60.00",
  "currency": "BDT"
}
```

## Example 95

`GET /api/practice-areas/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Family Law",
      "slug": "family-law"
    }
  ]
}
```

## Example 96

`GET /api/practice-areas/family-law/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "name": "Family Law",
  "slug": "family-law"
}
```

## Example 97

`GET /api/rights-topics/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "slug": "sample-getting-help",
      "title": "Sample: getting help"
    }
  ]
}
```

## Example 98

`GET /api/rights-topics/sample-getting-help/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "slug": "sample-getting-help",
  "title": "Sample: getting help"
}
```

## Example 99

`POST /api/session-registrations/`

Request body (JSON):

```json
{
  "session": 1,
  "name": "Sample Attendee",
  "email": "sample@example.test"
}
```

Response: **201** (representative excerpt).

```json
{
  "id": 1,
  "session": 1,
  "status": "registered"
}
```

## Example 100

`GET /api/tasks/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "case": 1,
      "title": "Prepare sample documents",
      "assigned_to": 2,
      "due_date": "2030-01-15",
      "status": "pending"
    }
  ]
}
```

## Example 101

`POST /api/tasks/`

Request body (JSON):

```json
{
  "case": 1,
  "title": "Prepare sample documents",
  "assigned_to": 2,
  "due_date": "2030-01-15"
}
```

Response: **201** (representative excerpt).

```json
{
  "id": 1,
  "case": 1,
  "title": "Prepare sample documents",
  "assigned_to": 2,
  "due_date": "2030-01-15",
  "status": "pending"
}
```

## Example 102

`DELETE /api/tasks/1/`

Request body: none.

Response: **204** (no response body).

## Example 103

`GET /api/tasks/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "case": 1,
  "title": "Prepare sample documents",
  "assigned_to": 2,
  "due_date": "2030-01-15",
  "status": "pending"
}
```

## Example 104

`PATCH /api/tasks/1/`

Request body (JSON):

```json
{
  "title": "Updated sample title"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "case": 1,
  "title": "Updated sample title",
  "assigned_to": 2,
  "due_date": "2030-01-15",
  "status": "pending"
}
```

## Example 105

`PUT /api/tasks/1/`

Request body (JSON):

```json
{
  "case": 1,
  "title": "Prepare sample documents",
  "assigned_to": 2,
  "due_date": "2030-01-15"
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 1,
  "case": 1,
  "title": "Prepare sample documents",
  "assigned_to": 2,
  "due_date": "2030-01-15",
  "status": "pending"
}
```

## Example 106

`GET /api/tasks/my-tasks/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "case": 1,
      "title": "Prepare sample documents",
      "assigned_to": 2,
      "due_date": "2030-01-15",
      "status": "pending"
    }
  ]
}
```

## Example 107

`GET /api/users/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 2,
      "username": "sample_lawyer",
      "full_name": "Sample Lawyer",
      "role": "lawyer",
      "is_active": true
    }
  ]
}
```

## Example 108

`POST /api/users/`

Request body (JSON):

```json
{
  "username": "sample_lawyer",
  "first_name": "Sample",
  "last_name": "Lawyer",
  "role": "lawyer",
  "password": "<initial-password>"
}
```

Response: **201** (representative excerpt).

```json
{
  "id": 2,
  "username": "sample_lawyer",
  "full_name": "Sample Lawyer",
  "role": "lawyer",
  "is_active": true
}
```

## Example 109

`GET /api/users/1/`

Request body: none.

Response: **200** (representative excerpt).

```json
{
  "id": 2,
  "username": "sample_lawyer",
  "full_name": "Sample Lawyer",
  "role": "lawyer",
  "is_active": true
}
```

## Example 110

`PATCH /api/users/1/`

Request body (JSON):

```json
{
  "is_active": false
}
```

Response: **200** (representative excerpt).

```json
{
  "id": 2,
  "username": "sample_lawyer",
  "full_name": "Sample Lawyer",
  "role": "lawyer",
  "is_active": false
}
```
