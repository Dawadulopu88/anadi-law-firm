# API permission matrix

Generated from the independent access contract in `accounts/test_integration.py`.
Run the full test suite to verify it. The matrix test uses real JWTs for all five roles.

Coverage: **110 canonical route/method combinations × 5 roles = 550 probes**.

A = access gate permits processing: list/read returns 200, empty write returns 400,
or a deliberately missing detail ID returns 404. A does not grant access to every record.
401 = anonymous denied; 403 = authenticated role denied. Real-object ownership,
valid writes, hidden notes/documents and revoked assignments are tested by the
end-to-end workflow and the feature regression suites. Format-suffix aliases, HEAD
and OPTIONS are equivalent protocol variants, not additional business operations.

| Method | Route | Anonymous | Client | Staff | Lawyer | Admin |
|---|---|---|---|---|---|---|
| GET | `/api/` | 401 | A | A | A | A |
| GET | `/api/appointments/` | 401 | A | A | A | A |
| POST | `/api/appointments/` | 401 | 403 | A | A | A |
| DELETE | `/api/appointments/<pk>/` | 401 | 403 | A | A | A |
| GET | `/api/appointments/<pk>/` | 401 | A | A | A | A |
| PATCH | `/api/appointments/<pk>/` | 401 | 403 | A | A | A |
| PUT | `/api/appointments/<pk>/` | 401 | 403 | A | A | A |
| GET | `/api/articles/` | A | A | A | A | A |
| GET | `/api/articles/<slug>/` | A | A | A | A | A |
| POST | `/api/auth/change-password/` | 401 | A | A | A | A |
| GET | `/api/auth/me/` | 401 | A | A | A | A |
| POST | `/api/auth/token/` | A | A | A | A | A |
| POST | `/api/auth/token/refresh/` | A | A | A | A | A |
| GET | `/api/case-assignments/` | 401 | 403 | A | A | A |
| POST | `/api/case-assignments/` | 401 | 403 | A | 403 | A |
| DELETE | `/api/case-assignments/<pk>/` | 401 | 403 | A | 403 | A |
| GET | `/api/case-assignments/<pk>/` | 401 | 403 | A | A | A |
| GET | `/api/case-notes/` | 401 | A | A | A | A |
| POST | `/api/case-notes/` | 401 | 403 | A | A | A |
| GET | `/api/case-notes/<pk>/` | 401 | A | A | A | A |
| GET | `/api/cases/` | 401 | A | A | A | A |
| POST | `/api/cases/` | 401 | 403 | A | 403 | A |
| GET | `/api/cases/<pk>/` | 401 | A | A | A | A |
| PATCH | `/api/cases/<pk>/` | 401 | 403 | A | A | A |
| PUT | `/api/cases/<pk>/` | 401 | 403 | A | A | A |
| GET | `/api/clients/` | 401 | A | A | A | A |
| POST | `/api/clients/` | 401 | 403 | A | A | A |
| GET | `/api/clients/<pk>/` | 401 | A | A | A | A |
| PATCH | `/api/clients/<pk>/` | 401 | 403 | A | A | A |
| PUT | `/api/clients/<pk>/` | 401 | 403 | A | A | A |
| GET | `/api/consultations/` | 401 | 403 | A | A | A |
| POST | `/api/consultations/` | A | A | A | A | A |
| GET | `/api/consultations/<pk>/` | 401 | 403 | A | A | A |
| PATCH | `/api/consultations/<pk>/` | 401 | 403 | A | A | A |
| PUT | `/api/consultations/<pk>/` | 401 | 403 | A | A | A |
| POST | `/api/consultations/<pk>/convert/` | 401 | 403 | A | A | A |
| GET | `/api/courses/` | A | A | A | A | A |
| GET | `/api/courses/<pk>/` | A | A | A | A | A |
| GET | `/api/documents/` | 401 | A | A | A | A |
| POST | `/api/documents/` | 401 | 403 | A | A | A |
| GET | `/api/documents/<pk>/` | 401 | A | A | A | A |
| PATCH | `/api/documents/<pk>/` | 401 | 403 | A | A | A |
| PUT | `/api/documents/<pk>/` | 401 | 403 | A | A | A |
| GET | `/api/documents/<pk>/download/` | 401 | A | A | A | A |
| GET | `/api/faqs/` | A | A | A | A | A |
| GET | `/api/faqs/<pk>/` | A | A | A | A | A |
| GET | `/api/firm/profile/` | A | A | A | A | A |
| GET | `/api/guided-flows/` | A | A | A | A | A |
| GET | `/api/guided-flows/<pk>/` | A | A | A | A | A |
| GET | `/api/guided-flows/<pk>/start/` | A | A | A | A | A |
| GET | `/api/guided-options/<pk>/result/` | A | A | A | A | A |
| GET | `/api/guided-questions/<pk>/` | A | A | A | A | A |
| GET | `/api/hearings/` | 401 | A | A | A | A |
| POST | `/api/hearings/` | 401 | 403 | A | A | A |
| DELETE | `/api/hearings/<pk>/` | 401 | 403 | A | A | A |
| GET | `/api/hearings/<pk>/` | 401 | A | A | A | A |
| PATCH | `/api/hearings/<pk>/` | 401 | 403 | A | A | A |
| PUT | `/api/hearings/<pk>/` | 401 | 403 | A | A | A |
| GET | `/api/hearings/upcoming/` | 401 | A | A | A | A |
| GET | `/api/help-contacts/` | A | A | A | A | A |
| GET | `/api/invoices/` | 401 | A | A | A | A |
| POST | `/api/invoices/` | 401 | 403 | A | A | A |
| DELETE | `/api/invoices/<pk>/` | 401 | 403 | A | A | A |
| GET | `/api/invoices/<pk>/` | 401 | A | A | A | A |
| PATCH | `/api/invoices/<pk>/` | 401 | 403 | A | A | A |
| PUT | `/api/invoices/<pk>/` | 401 | 403 | A | A | A |
| GET | `/api/jurisdictions/` | A | A | A | A | A |
| GET | `/api/jurisdictions/<code>/` | A | A | A | A | A |
| GET | `/api/knowledge/search/` | A | A | A | A | A |
| GET | `/api/lawyers/` | A | A | A | A | A |
| GET | `/api/lawyers/<pk>/` | A | A | A | A | A |
| GET | `/api/legal-aid/applications/` | 401 | 403 | A | A | A |
| GET | `/api/legal-aid/applications/<pk>/` | 401 | 403 | A | A | A |
| PATCH | `/api/legal-aid/applications/<pk>/` | 401 | 403 | A | A | A |
| PUT | `/api/legal-aid/applications/<pk>/` | 401 | 403 | A | A | A |
| POST | `/api/legal-aid/applications/<pk>/convert/` | 401 | 403 | A | A | A |
| POST | `/api/legal-aid/apply/` | A | A | A | A | A |
| GET | `/api/legal-aid/track/<code>/` | A | A | A | A | A |
| GET | `/api/live-sessions/` | A | A | A | A | A |
| GET | `/api/live-sessions/<pk>/` | A | A | A | A | A |
| GET | `/api/pathways/` | A | A | A | A | A |
| GET | `/api/pathways/<slug>/` | A | A | A | A | A |
| GET | `/api/payments/` | 401 | 403 | A | A | A |
| POST | `/api/payments/` | 401 | 403 | A | A | A |
| DELETE | `/api/payments/<pk>/` | 401 | 403 | A | A | A |
| GET | `/api/payments/<pk>/` | 401 | 403 | A | A | A |
| PATCH | `/api/payments/<pk>/` | 401 | 403 | A | A | A |
| PUT | `/api/payments/<pk>/` | 401 | 403 | A | A | A |
| GET | `/api/portal/appointments/` | 401 | A | 403 | 403 | 403 |
| GET | `/api/portal/cases/` | 401 | A | 403 | 403 | 403 |
| GET | `/api/portal/documents/` | 401 | A | 403 | 403 | 403 |
| GET | `/api/portal/hearings/` | 401 | A | 403 | 403 | 403 |
| GET | `/api/portal/invoices/` | 401 | A | 403 | 403 | 403 |
| GET | `/api/portal/summary/` | 401 | A | 403 | 403 | 403 |
| GET | `/api/practice-areas/` | A | A | A | A | A |
| GET | `/api/practice-areas/<slug>/` | A | A | A | A | A |
| GET | `/api/rights-topics/` | A | A | A | A | A |
| GET | `/api/rights-topics/<slug>/` | A | A | A | A | A |
| POST | `/api/session-registrations/` | A | A | A | A | A |
| GET | `/api/tasks/` | 401 | 403 | A | A | A |
| POST | `/api/tasks/` | 401 | 403 | A | A | A |
| DELETE | `/api/tasks/<pk>/` | 401 | 403 | A | A | A |
| GET | `/api/tasks/<pk>/` | 401 | 403 | A | A | A |
| PATCH | `/api/tasks/<pk>/` | 401 | 403 | A | A | A |
| PUT | `/api/tasks/<pk>/` | 401 | 403 | A | A | A |
| GET | `/api/tasks/my-tasks/` | 401 | 403 | A | A | A |
| GET | `/api/users/` | 401 | 403 | A | A | A |
| POST | `/api/users/` | 401 | 403 | 403 | 403 | A |
| GET | `/api/users/<pk>/` | 401 | 403 | A | A | A |
| PATCH | `/api/users/<pk>/` | 401 | 403 | 403 | 403 | A |

## Object scope

- Admin/staff: all cases. Lawyers: assigned cases only. Clients: their linked client records only.
- Notes: clients see shared notes only. Documents: clients need ownership and client visibility.
- Tasks: firm roles only; lawyers see assigned-case tasks and their own standalone tasks.
- Clients, consultations, appointments, billing and legal-aid staff APIs retain the existing firm-wide access policy for all three firm roles.
- Portal routes accept client-role tokens only, and always restrict records to that account.
- Public knowledge requires publication/review and active related records; contacts require verification.
- Admin UI also requires Django staff/model permissions. Account administration additionally requires the application admin role.
- No public user-registration API exists. Provision client logins through authorised account administration.
