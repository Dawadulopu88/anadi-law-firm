"""Build/check a complete route index with curated, fictional API examples."""
import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from accounts.test_integration import allowed_roles, api_routes

# Examples are excerpts, not fixtures or promises that ID 1 exists in a database.
SAMPLES = {
    'firm': {'name': 'Anadi Law Firm', 'tagline': 'Sample website', 'logo': 'http://127.0.0.1:8000/static/firm/anadi-law-firm.png'},
    'practice-areas': {'id': 1, 'name': 'Family Law', 'slug': 'family-law'},
    'lawyers': {'id': 1, 'full_name': 'Sample Lawyer', 'practice_areas': []},
    'clients': {'id': 1, 'full_name': 'Sample Client', 'status': 'active'},
    'consultations': {'id': 1, 'name': 'Sample Visitor', 'status': 'new', 'client': None},
    'appointments': {'id': 1, 'client': 1, 'lawyer': 2, 'case': 1, 'start': '2030-01-15T10:00:00+06:00', 'end': '2030-01-15T11:00:00+06:00', 'status': 'scheduled'},
    'cases': {'id': 1, 'case_number': 'SAMPLE-001', 'title': 'Sample case', 'status': 'open', 'court': 'Sample court', 'lead_lawyers': []},
    'case-assignments': {'id': 1, 'case': 1, 'user': 2, 'lawyer': 2, 'role': 'lead'},
    'case-notes': {'id': 1, 'case': 1, 'body': 'Sample shared update', 'is_internal': False},
    'hearings': {'id': 1, 'case': 1, 'court_name': 'Sample court', 'hearing_at': '2030-01-16T10:00:00+06:00'},
    'tasks': {'id': 1, 'case': 1, 'title': 'Prepare sample documents', 'assigned_to': 2, 'due_date': '2030-01-15', 'status': 'pending'},
    'documents': {'id': 1, 'case': 1, 'title': 'Sample document', 'version': 1, 'download_url': '/api/documents/1/download/'},
    'invoices': {'id': 1, 'invoice_number': 'SAMPLE-INV-001', 'amount': '100.00', 'paid_amount': '40.00', 'balance': '60.00', 'status': 'partial', 'currency': 'BDT'},
    'payments': {'id': 1, 'invoice': 1, 'amount': '40.00', 'method': 'cash', 'date': '2030-01-15'},
    'legal-aid': {'id': 1, 'applicant_name': 'Sample Applicant', 'status': 'submitted'},
    'jurisdictions': {'id': 1, 'code': 'bd', 'name': 'Bangladesh', 'is_active': True},
    'rights-topics': {'id': 1, 'slug': 'sample-getting-help', 'title': 'Sample: getting help'},
    'articles': {'id': 1, 'slug': 'sample-help-en', 'title': 'Sample: consultation information', 'body': 'Demonstration placeholder.', 'language': 'en', 'is_sample': True, 'disclaimer': 'General information, not legal advice.'},
    'faqs': {'id': 1, 'question': 'Sample question', 'answer': 'Demonstration placeholder.', 'language': 'en', 'disclaimer': 'General information, not legal advice.'},
    'knowledge': {'type': 'article', 'id': 1, 'title': 'Sample: consultation information', 'language': 'en'},
    'help-contacts': {'id': 1, 'label': 'Example verified contact', 'phone': '<verified-number>', 'hours': '', 'is_emergency': False},
    'guided-flows': {'id': 1, 'name': 'Sample: finding help', 'purpose': 'issue_finder', 'start_question': 1, 'is_sample': True},
    'guided-questions': {'id': 1, 'flow': 1, 'text': 'What would you like to discuss?', 'order': 0, 'options': [{'id': 1, 'label': 'Another matter', 'next_question': None}]},
    'guided-options': {'practice_area': None, 'articles': [], 'consultation_url': '/api/consultations/', 'escalate_to_consultation': True, 'indicative_only': True, 'is_sample': True},
    'pathways': {'id': 1, 'slug': 'sample-learning', 'title': 'Sample: learning pathway', 'is_sample': True},
    'courses': {'id': 1, 'pathway': 1, 'title': 'Sample: finding support', 'level': 'beginner', 'duration': '1 hour', 'is_sample': True},
    'live-sessions': {'id': 1, 'title': 'Sample session', 'start': '2030-01-15T10:00:00+06:00', 'capacity': 10, 'seats_remaining': 9, 'is_sample': True},
    'session-registrations': {'id': 1, 'session': 1, 'status': 'registered'},
    'auth': {'id': 1, 'username': 'sample_client', 'role': 'client'},
    'users': {'id': 2, 'username': 'sample_lawyer', 'full_name': 'Sample Lawyer', 'role': 'lawyer', 'is_active': True},
}
WRITES = {
    'clients': {'full_name': 'Sample Client', 'user': 3, 'status': 'active'},
    'consultations': {'name': 'Sample Visitor', 'phone': 'DEMO-NOT-A-PHONE', 'practice_area': 1, 'message': 'Fictional request', 'preferred_language': 'en'},
    'appointments': {'client': 1, 'lawyer': 2, 'case': 1, 'start': '2030-01-15T10:00:00+06:00', 'end': '2030-01-15T11:00:00+06:00', 'appointment_type': 'consultation'},
    'cases': {'case_number': 'SAMPLE-001', 'title': 'Sample case', 'client': 1, 'practice_area': 1, 'court': 'Sample court', 'priority': 'normal'},
    'case-assignments': {'case': 1, 'user': 2, 'role': 'lead'},
    'case-notes': {'case': 1, 'body': 'Sample shared update', 'is_internal': False},
    'hearings': {'case': 1, 'court_name': 'Sample court', 'hearing_at': '2030-01-16T10:00:00+06:00'},
    'tasks': {'case': 1, 'title': 'Prepare sample documents', 'assigned_to': 2, 'due_date': '2030-01-15'},
    'documents': {'case': 1, 'title': 'Sample document', 'document_type': 'sample', 'version': 1, 'file': '<binary sample.txt>'},
    'invoices': {'invoice_number': 'SAMPLE-INV-001', 'client': 1, 'case': 1, 'issue_date': '2030-01-15', 'due_date': '2030-01-22', 'amount': '100.00'},
    'payments': {'invoice': 1, 'amount': '40.00', 'method': 'cash', 'date': '2030-01-15'},
    'legal-aid': {'status': 'under_review'},
    'session-registrations': {'session': 1, 'name': 'Sample Attendee', 'email': 'sample@example.test'},
    'users': {'username': 'sample_lawyer', 'first_name': 'Sample', 'last_name': 'Lawyer', 'role': 'lawyer', 'password': '<initial-password>'},
}


def example(route, method, action):
    root = route.split('/')[2]
    if route == '/api/':
        return None, {'pathways': 'http://127.0.0.1:8000/api/pathways/'}, 200
    if route.startswith('/api/auth/token/'):
        refresh = 'refresh/' in route
        return ({'refresh': '<refresh-token>'} if refresh else {'username': '<your-username>', 'password': '<your-password>'},
                {'access': '<access-token>'} if refresh else {'access': '<access-token>', 'refresh': '<refresh-token>'}, 200)
    if root == 'portal':
        resource = route.strip('/').split('/')[-1]
        if resource == 'summary':
            return None, {'cases': 1, 'active_cases': 1, 'upcoming_hearings': 1, 'upcoming_appointments': 1,
                          'documents': 0, 'invoices': 1, 'outstanding_balance': '60.00', 'currency': 'BDT'}, 200
        item = dict(SAMPLES[resource])
        for field in ('client', 'lawyer', 'is_internal'):
            item.pop(field, None)
        if resource == 'appointments':
            item['lawyer_name'] = 'Sample Lawyer'
        return None, {'count': 1, 'next': None, 'previous': None, 'results': [item]}, 200
    if '/convert/' in route:
        if root == 'consultations':
            return {}, {'consultation_id': 1, 'client_id': 1, 'status': 'converted', 'created': True}, 201
        return {}, {'client': 1, 'case': 1, 'status': 'matched', 'created': True}, 201
    if '/legal-aid/apply/' in route:
        return {'applicant_name': 'Sample Applicant', 'phone': 'DEMO-NOT-A-PHONE', 'practice_area': 1,
                'description': 'Fictional request', 'eligibility_answers': {'demo_only': True}}, {'tracking_code': '<private-tracking-code>', 'status': 'submitted'}, 201
    if '/legal-aid/track/' in route:
        return None, {'status': 'submitted'}, 200
    if route == '/api/auth/change-password/':
        return {'current_password': '<current-password>', 'new_password': '<new-password>'}, {'detail': 'Password changed.'}, 200
    if action == 'start':
        return None, {'flow': SAMPLES['guided-flows'], 'question': SAMPLES['guided-questions'], 'indicative_only': True, 'disclaimer': 'General information, not legal advice.'}, 200
    if action == 'download':
        return None, '<binary file attachment; not JSON>', 200
    sample = dict(SAMPLES[root])
    if method == 'delete':
        return None, None, 204
    request = None
    if method in ('post', 'put', 'patch'):
        request = dict(WRITES[root])
        if root == 'consultations' and method != 'post':
            request = {'status': 'contacted'}
        elif root == 'documents' and method != 'post':
            request.pop('file')
        elif method == 'patch':
            request = ({'title': 'Updated sample title'} if 'title' in request else
                       {'amount': '50.00'} if root in ('invoices', 'payments') else
                       {'full_name': 'Updated sample name'} if root == 'clients' else
                       {'court_name': 'Updated sample court'} if root == 'hearings' else
                       {'status': 'cancelled'} if root == 'appointments' else
                       {'is_active': False} if root == 'users' else request)
        if root == 'consultations' and method == 'post':
            sample = {'id': 1, 'status': 'new'}
        elif root == 'invoices' and method == 'post':
            sample.update(paid_amount='0.00', balance='100.00', status='unpaid')
        if method in ('patch', 'put'):
            sample.update({key: value for key, value in request.items() if key in sample})
            if root == 'invoices':
                sample.update(balance='10.00' if method == 'patch' else '60.00')
    if method == 'get' and (action in ('list', 'upcoming', 'my_tasks') or root in ('knowledge', 'help-contacts') or route in ('/api/practice-areas/', '/api/lawyers/')):
        sample = {'count': 1, 'next': None, 'previous': None, 'results': [sample]}
    return request, sample, 201 if method == 'post' else 200


def render():
    routes = sorted(set(api_routes()))
    lines = ['# Complete backend API reference', '',
        'Generated with `python scripts/api_reference.py`; use `--check` to detect drift.', '',
        '## Conventions', '',
        '- Base URL locally: `http://127.0.0.1:8000`. This is not a hosted production URL.',
        '- JSON bodies use `Content-Type: application/json`. Private APIs require `Authorization: Bearer <access-token>`.',
        '- Send `Accept-Language: en` or `bn` for bilingual fields; missing translations fall back to English.',
        '- Lists use `{count, next, previous, results}` and page size 20; use `?page=2`.',
        '- Examples below are fictional response excerpts. IDs are illustrative: obtain actual IDs from list/create responses.',
        '- Date examples are illustrative; time-sensitive operations require valid future dates. Datetimes accept ISO 8601 offsets.',
        '- Server-controlled IDs, ownership actors and timestamps are read-only. Client-role serializers omit internal fields.',
        '- PATCH changes supplied fields; PUT supplies the writable required fields shown in its example. Ownership cannot be transferred.',
        '- POST creation normally returns 201; update/read returns 200; DELETE returns 204 with no body.',
        '- Validation errors use field-to-message-list objects, e.g. `{"amount":["Payment exceeds the remaining invoice balance."]}`.',
        '- General errors use `{"detail":"..."}`. Handle 400 (invalid), 401 (login), 403 (role), 404 (missing/inaccessible), 405 (unsupported method), 429 (rate limit).',
        '- Do not depend on exact English error text. Custom messages are not all translated to Bangla.',
        '- Login/refresh share 20 requests/min/IP. Consultation forms: 5/min and 30/day. Legal-aid/Academy forms share 5/min and 30/day. Tracking: 100/hour.',
        '- Browser Admin cookies do not authenticate JWT APIs. No public account-signup endpoint exists.',
        '- All three firm roles can manage clients, appointments, consultations, invoices/payments and legal-aid records. Case resources are assignment-scoped for lawyers.',
        '- Client reads are ownership-scoped; notes must be shared, documents must be client-visible. Portal accepts client-role tokens only.',
        '- The `/api/` router landing response is not a complete endpoint index. Use this document for all modules.', '',
        '## Filters and special behaviour', '',
        '- Cases: `client`, `practice_area`, `status`, `lawyer`, `search`, `ordering`; ordering supports created_at, updated_at, filing_date and case_number (prefix `-` for descending).',
        '- Assignments, notes, hearings, tasks and documents: `case=<id>`. Invoices: `client=<id>`, `case=<id>`. Payments: `invoice=<id>`. Appointments (firm roles): `client`, `case`, `lawyer`, `status`. Consultations and legal-aid applications: `status`. Users: `role` (comma-separated), `search`, `without_client=1`. Clients (firm roles): `assigned_lawyer`, `status`, `search`.',
        '- Articles/FAQs/search: `jurisdiction=<code>`, `topic=<slug>`, `language=en|bn`. Search requires `q` (1–200 characters).',
        '- Courses: `pathway=<id>`. Live sessions: `course=<id>`. Only future published sessions with available parent content are listed.',
        '- Jurisdiction detail uses code; practice areas/topics/articles/pathways use slug; other detail routes use numeric ID.',
        '- Only reviewed/published knowledge and verified help contacts are public. Seeds leave legal content as drafts.',
        '- Conversion actions are idempotent: repeat returns 200 with `created:false` and the existing linked IDs.',
        '- Assignments accept `user` and role lead/support. Legacy `lawyer` is supported for lawyers only; never send both.',
        '- Cases support court, opposite_party, priority low/normal/high and closed_date. Closed dates require closed/archived status and cannot precede filing.',
        '- Notes and assignments cannot be edited through the API. Correct a note with a new note; change an assignment by removing/recreating it.',
        '- Documents: POST multipart/form-data with the named fields and a real file part. Allowed PDF/PNG/JPEG/UTF-8 TXT, nonempty, maximum 10 MB. File and case are immutable.',
        '- Document PATCH/PUT edits metadata only. Download is binary with attachment, nosniff and no-store headers; storage paths are never public.',
        '- Invoices use BDT and derive paid/partial/unpaid status from payments. Payments cannot exceed the balance; invoices with payments cannot be deleted.',
        '- Public form `website` is an optional honeypot: omit or leave blank. Legal-aid answers allow at most 20 short scalar values, 5000 total JSON characters.',
        '- Tracking codes are confidential receipt identifiers. Public tracking returns status only, with no-store headers.',
        '- Session registration normalizes email, rejects duplicates and full/closed sessions. There is no public participant-list endpoint.',
        '- Guided flow: read start, show question/options, follow next_question when present; otherwise GET the selected option result. Results are indicative, not eligibility decisions.', '',
        '## Endpoint index', '', f'All **{len(routes)} canonical route/method combinations** are listed. HEAD/OPTIONS and format suffixes are protocol aliases.', '',
        '| Method | Route | Who may call | Example |', '|---|---|---|---|']
    for index, (route, method, _) in enumerate(routes, 1):
        roles = allowed_roles(route, method)
        who = 'Public' if 'anonymous' in roles else ', '.join(roles)
        lines.append(f'| {method.upper()} | `{route}` | {who} | [Example {index}](#example-{index}) |')
    for index, (route, method, action) in enumerate(routes, 1):
        request, response, status = example(route, method, action)
        concrete = re.sub(r'<[^>]+>', '1', route)
        concrete = concrete.replace('/jurisdictions/1/', '/jurisdictions/bd/').replace('/pathways/1/', '/pathways/sample-learning/').replace('/articles/1/', '/articles/sample-help-en/').replace('/rights-topics/1/', '/rights-topics/sample-getting-help/').replace('/practice-areas/1/', '/practice-areas/family-law/')
        if '/knowledge/search/' in route:
            concrete += '?q=sample'
        if '/legal-aid/track/' in route:
            concrete = '/api/legal-aid/track/<your-private-tracking-code>/'
        lines += ['', f'## Example {index}', '', f'`{method.upper()} {concrete}`', '']
        if request is None:
            lines += ['Request body: none.']
        else:
            lines += ['Request body' + (' (multipart fields; file is a binary part)' if '/documents/' in route and method == 'post' else ' (JSON)') + ':', '', '```json', json.dumps(request, ensure_ascii=False, indent=2), '```']
        lines += ['', f'Response: **{status}**' + (' (representative excerpt).' if response is not None else ' (no response body).')]
        if isinstance(response, dict):
            lines += ['', '```json', json.dumps(response, ensure_ascii=False, indent=2), '```']
        elif response:
            lines += ['', response]
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'docs' / 'API_REFERENCE.md'
    content = render()
    if args.check:
        if not path.exists() or path.read_text(encoding='utf-8') != content:
            raise SystemExit('API reference is stale; regenerate it.')
        print('API reference matches all discovered routes and curated examples.')
    else:
        path.write_text(content, encoding='utf-8')
        print(f'Wrote {path}')
