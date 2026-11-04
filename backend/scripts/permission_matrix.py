r"""Render the access contract exercised by accounts.test_integration.

Run from the repository root: .venv\Scripts\python.exe scripts/permission_matrix.py
This generates documentation only; run the tests to verify its assertions.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from accounts.test_integration import ROLES, allowed_roles, api_routes

routes = sorted(set(api_routes()))
lines = [
    '# API permission matrix', '',
    'Generated from the independent access contract in `accounts/test_integration.py`.',
    'Run the full test suite to verify it. The matrix test uses real JWTs for all five roles.', '',
    f'Coverage: **{len(routes)} canonical route/method combinations × 5 roles = {len(routes) * 5} probes**.', '',
    'A = access gate permits processing: list/read returns 200, empty write returns 400,',
    'or a deliberately missing detail ID returns 404. A does not grant access to every record.',
    '401 = anonymous denied; 403 = authenticated role denied. Real-object ownership,',
    'valid writes, hidden notes/documents and revoked assignments are tested by the',
    'end-to-end workflow and the feature regression suites. Format-suffix aliases, HEAD',
    'and OPTIONS are equivalent protocol variants, not additional business operations.', '',
    '| Method | Route | Anonymous | Client | Staff | Lawyer | Admin |',
    '|---|---|---|---|---|---|---|',
]
for route, method, action in routes:
    allowed = allowed_roles(route, method)
    results = ['A' if role in allowed else ('401' if role == 'anonymous' else '403') for role in ROLES]
    lines.append('| ' + ' | '.join([method.upper(), '`' + route + '`', *results]) + ' |')
lines += ['', '## Object scope', '',
          '- Admin/staff: all cases. Lawyers: assigned cases only. Clients: their linked client records only.',
          '- Notes: clients see shared notes only. Documents: clients need ownership and client visibility.',
          '- Tasks: firm roles only; lawyers see assigned-case tasks and their own standalone tasks.',
          '- Clients, consultations, appointments, billing and legal-aid staff APIs retain the existing firm-wide access policy for all three firm roles.',
          '- Portal routes accept client-role tokens only, and always restrict records to that account.',
          '- Public knowledge requires publication/review and active related records; contacts require verification.',
          '- Admin UI also requires Django staff/model permissions. Account administration additionally requires the application admin role.',
          '- No public user-registration API exists. Provision client logins through authorised account administration.', '']
(ROOT / 'docs' / 'PERMISSIONS.md').write_text('\n'.join(lines), encoding='utf-8')
print(f'Wrote matrix: {len(routes)} route/method combinations, {len(routes) * 5} role probes.')
