import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, downloadFile } from '../../api/client';
import ResourceManager, { FormModal as FormModalLazy } from '../../components/ResourceManager';
import { Badge, Confirm } from '../../components/UI';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { fmtDate, fmtDateTime, label, money, todayISO } from '../../utils/format';
import { byId, invalidateLookup, useLookups } from '../../utils/hooks';

export const opts = (list, text = 'name', value = 'id') => list.map((x) => ({ value: x[value], label: typeof text === 'function' ? text(x) : x[text] }));
export const choice = (...values) => values.map((v) => ({ value: v, label: label(v) }));
const userName = (users, id) => byId(users, id)?.full_name || (id ? `#${id}` : '—');
const caseLabel = (cases, id) => { const c = byId(cases, id); return c ? `${c.case_number}` : id ? `#${id}` : '—'; };
const clientName = (clients, id) => byId(clients, id)?.full_name || (id ? `#${id}` : '—');

/* ---------------- Clients ---------------- */
export function Clients() {
  const { users, refresh } = useLookups(['users']);
  const fields = (row) => [
    { name: 'full_name', label: 'Full name', required: true },
    { name: 'phone', label: 'Phone' },
    { name: 'email', label: 'Email', type: 'email' },
    { name: 'status', label: 'Status', type: 'select', options: choice('active', 'inactive', 'archived'), default: 'active' },
    { name: 'assigned_lawyer', label: 'Assigned lawyer', type: 'select', nullable: true, options: opts(users.filter((u) => u.role === 'lawyer' && (u.is_active || (row && u.id === row.assigned_lawyer))), 'full_name') },
    { name: 'nid_or_reference', label: 'NID / reference' },
    {
      name: 'user', label: 'Portal login (client account)', type: 'select', nullable: true,
      hint: 'Link a client-role user so they can use the portal.',
      options: users.filter((u) => u.role === 'client' && (!u.has_client_record || (row && u.id === row.user))).map((u) => ({ value: u.id, label: `${u.full_name} (@${u.username})` })),
    },
    { name: 'address', label: 'Address', type: 'textarea', full: true, rows: 2 },
    { name: 'notes', label: 'Internal notes (never shown to client)', type: 'textarea', full: true },
  ];
  return (
    <ResourceManager title="Clients" endpoint="/api/clients/" createLabel="New client" fields={fields}
      filters={[
        { name: 'search', type: 'search', label: 'Search name, phone, email…' },
        { name: 'status', label: 'All statuses', options: choice('active', 'inactive', 'archived') },
        { name: 'assigned_lawyer', label: 'All lawyers', options: opts(users.filter((u) => u.role === 'lawyer'), 'full_name') },
      ]}
      onMutate={() => { invalidateLookup('clients'); refresh(); }}
      columns={[
        { key: 'full_name', label: 'Name', strong: true },
        { key: 'phone', label: 'Phone' },
        { key: 'email', label: 'Email', render: (r) => r.email || '—' },
        { key: 'assigned_lawyer', label: 'Lawyer', render: (r) => r.assigned_lawyer_name || <span className="muted">Unassigned</span> },
        { key: 'user', label: 'Portal', render: (r) => (r.user ? <Badge tone="green">Linked</Badge> : <Badge tone="grey">No login</Badge>) },
        { key: 'status', label: 'Status', render: (r) => <Badge value={r.status} /> },
        { key: 'created_at', label: 'Added', render: (r) => fmtDate(r.created_at) },
      ]} />
  );
}

/* ---------------- Consultations ---------------- */
export function Consultations() {
  const toast = useToast();
  const navigate = useNavigate();
  const { practiceAreas } = useLookups(['practiceAreas']);
  const [converting, setConverting] = useState(null);
  const [busy, setBusy] = useState(false);
  const [key, setKey] = useState(0);
  const convert = async () => {
    setBusy(true);
    try {
      const r = await api.post(`/api/consultations/${converting.id}/convert/`, {});
      invalidateLookup('clients');
      toast.success(r.created ? 'Client record created from consultation' : 'Already converted');
      setConverting(null); setKey((k) => k + 1);
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return (
    <>
      <ResourceManager title="Consultation requests" endpoint="/api/consultations/" canCreate={false} reloadKey={key}
        filters={[{ name: 'status', label: 'All statuses', options: choice('new', 'contacted', 'converted', 'closed') }]}
        canEdit={(r) => r.status !== 'converted'}
        fields={[{ name: 'status', label: 'Status', type: 'select', required: true, options: choice('new', 'contacted', 'closed'), full: true }]}
        columns={[
          { key: 'name', label: 'Name', strong: true, render: (r) => <div>{r.name}<div className="small muted">{r.phone}{r.email ? ` · ${r.email}` : ''}</div></div> },
          { key: 'practice_area', label: 'Area', render: (r) => byId(practiceAreas, r.practice_area)?.name || '—' },
          { key: 'message', label: 'Message', render: (r) => <span title={r.message}>{r.message.slice(0, 70)}{r.message.length > 70 ? '…' : ''}</span> },
          { key: 'preferred_date', label: 'Preferred', render: (r) => <>{fmtDate(r.preferred_date)}<div className="small muted">{r.preferred_language === 'bn' ? 'Bangla' : 'English'}</div></> },
          { key: 'status', label: 'Status', render: (r) => <Badge value={r.status} /> },
          { key: 'created_at', label: 'Received', render: (r) => fmtDateTime(r.created_at) },
        ]}
        onMutate={() => invalidateLookup('clients')}
        rowActions={(r) => (r.status === 'converted'
          ? <button type="button" className="btn btn-xs btn-ghost" onClick={() => navigate('/dashboard/clients')}><i className="bi bi-person-check" /> Client #{r.client}</button>
          : r.status !== 'closed' && <button type="button" className="btn btn-xs btn-outline" onClick={() => setConverting(r)}><i className="bi bi-person-plus" /> Convert</button>)} />
      {converting && <Confirm title="Convert to client" message={`Create a client record for ${converting.name}? The consultation will be marked converted.`} confirmText="Convert" busy={busy} onConfirm={convert} onClose={() => setConverting(null)} />}
    </>
  );
}

/* ---------------- Legal aid ---------------- */
export function LegalAid() {
  const toast = useToast();
  const { practiceAreas } = useLookups(['practiceAreas']);
  const [converting, setConverting] = useState(null);
  const [viewing, setViewing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [key, setKey] = useState(0);
  const convert = async () => {
    setBusy(true);
    try {
      const r = await api.post(`/api/legal-aid/applications/${converting.id}/convert/`, {});
      invalidateLookup('clients', 'cases');
      toast.success(r.created ? `Matched: client #${r.client}, case #${r.case} created` : 'Already matched');
      setConverting(null); setKey((k) => k + 1);
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return (
    <>
      <ResourceManager title="Legal-aid applications" endpoint="/api/legal-aid/applications/" canCreate={false} reloadKey={key}
        filters={[{ name: 'status', label: 'All statuses', options: choice('submitted', 'under_review', 'matched', 'declined') }]}
        canEdit={(r) => r.status !== 'matched'}
        fields={[{ name: 'status', label: 'Status', type: 'select', required: true, options: choice('submitted', 'under_review', 'declined'), full: true }]}
        columns={[
          { key: 'applicant_name', label: 'Applicant', strong: true, render: (r) => <div>{r.applicant_name}<div className="small muted">{r.phone}</div></div> },
          { key: 'practice_area', label: 'Area', render: (r) => byId(practiceAreas, r.practice_area)?.name || '—' },
          { key: 'income_range', label: 'Income', render: (r) => r.income_range || '—' },
          { key: 'status', label: 'Status', render: (r) => <Badge value={r.status} /> },
          { key: 'created_at', label: 'Submitted', render: (r) => fmtDate(r.created_at) },
        ]}
        rowActions={(r) => (
          <>
            <button type="button" className="icon-btn" title="View" onClick={() => setViewing(r)}><i className="bi bi-eye" /></button>
            {r.status === 'matched' ? <Link className="btn btn-xs btn-ghost" to={`/dashboard/cases/${r.case}`}>Case #{r.case}</Link>
              : r.status !== 'declined' && <button type="button" className="btn btn-xs btn-outline" onClick={() => setConverting(r)}><i className="bi bi-link-45deg" /> Match</button>}
          </>
        )} />
      {converting && <Confirm title="Match application" message={`Create a client and a legal-aid case for ${converting.applicant_name}?`} confirmText="Create client & case" busy={busy} onConfirm={convert} onClose={() => setConverting(null)} />}
      {viewing && (
        <Confirm title={viewing.applicant_name} confirmText="Close" onConfirm={() => setViewing(null)} onClose={() => setViewing(null)} message={(
          <span style={{ display: 'block' }}>
            <span className="small muted">Description</span><br />
            <span style={{ whiteSpace: 'pre-wrap' }}>{viewing.description}</span><br /><br />
            <span className="small muted">Eligibility answers</span><br />
            {Object.entries(viewing.eligibility_answers || {}).map(([k, v]) => <span key={k} style={{ display: 'block' }}>{label(k)}: <b>{String(v)}</b></span>)}
            <br /><span className="small muted">Email: {viewing.email || '—'}</span>
          </span>
        )} />
      )}
    </>
  );
}

/* ---------------- Appointments ---------------- */
export function appointmentFields(clients, cases, users) {
  return [
    { name: 'client', label: 'Client', type: 'select', required: true, options: opts(clients, 'full_name'), onChangeReset: ['case'] },
    { name: 'case', label: 'Case (optional)', type: 'select', nullable: true, options: (v) => opts(cases.filter((c) => !v.client || String(c.client) === String(v.client)), (c) => `${c.case_number} — ${c.title}`) },
    { name: 'lawyer', label: 'Lawyer', type: 'select', required: true, options: opts(users.filter((u) => u.role === 'lawyer' && u.is_active), 'full_name') },
    { name: 'appointment_type', label: 'Type', type: 'select', options: choice('consultation', 'meeting', 'call'), default: 'consultation' },
    { name: 'start', label: 'Start', type: 'datetime', required: true },
    { name: 'end', label: 'End', type: 'datetime', required: true },
    { name: 'status', label: 'Status', type: 'select', options: choice('scheduled', 'completed', 'cancelled'), default: 'scheduled' },
    { name: 'notes', label: 'Internal notes', type: 'textarea', full: true, rows: 3 },
  ];
}

export function Appointments({ caseId, clientId }) {
  const { clients, cases, users } = useLookups(['clients', 'cases', 'users']);
  return (
    <ResourceManager title="Appointments" endpoint="/api/appointments/" createLabel="New appointment"
      baseQuery={caseId ? { case: caseId } : {}} defaults={{ case: caseId, client: clientId }}
      filters={caseId ? [] : [
        { name: 'status', label: 'All statuses', options: choice('scheduled', 'completed', 'cancelled') },
        { name: 'lawyer', label: 'All lawyers', options: opts(users.filter((u) => u.role === 'lawyer'), 'full_name') },
      ]}
      fields={appointmentFields(clients, cases, users)} canDelete={() => true}
      columns={[
        { key: 'start', label: 'When', strong: true, render: (r) => <>{fmtDateTime(r.start)}<div className="small muted">until {fmtDateTime(r.end).split(', ').pop()}</div></> },
        { key: 'client', label: 'Client', render: (r) => clientName(clients, r.client) },
        { key: 'lawyer', label: 'Lawyer', render: (r) => userName(users, r.lawyer) },
        { key: 'case', label: 'Case', render: (r) => (r.case ? <Link to={`/dashboard/cases/${r.case}`}>{caseLabel(cases, r.case)}</Link> : '—') },
        { key: 'appointment_type', label: 'Type', render: (r) => label(r.appointment_type) },
        { key: 'status', label: 'Status', render: (r) => <Badge value={r.status} /> },
      ]} />
  );
}

/* ---------------- Hearings ---------------- */
export function Hearings({ caseId }) {
  const { cases } = useLookups(['cases']);
  const [upcoming, setUpcoming] = useState(!caseId);
  return (
    <ResourceManager title="Hearings" endpoint="/api/hearings/" listPath={upcoming ? '/api/hearings/upcoming/' : '/api/hearings/'}
      createLabel="New hearing" baseQuery={caseId ? { case: caseId } : {}} defaults={{ case: caseId }} canDelete={() => true}
      headExtra={!caseId && (
        <div className="tabs mb-0" style={{ padding: 3 }}>
          <button type="button" className={upcoming ? 'on' : ''} onClick={() => setUpcoming(true)}>Upcoming</button>
          <button type="button" className={!upcoming ? 'on' : ''} onClick={() => setUpcoming(false)}>All</button>
        </div>
      )}
      fields={[
        { name: 'case', label: 'Case', type: 'select', required: true, lockOnEdit: true, hidden: !!caseId, options: opts(cases, (c) => `${c.case_number} — ${c.title}`) },
        { name: 'court_name', label: 'Court', required: true },
        { name: 'hearing_at', label: 'Hearing date & time', type: 'datetime', required: true },
        { name: 'case_number', label: 'Court case number' },
        { name: 'next_hearing_date', label: 'Next hearing', type: 'datetime', nullable: true },
        { name: 'outcome', label: 'Outcome', type: 'textarea', full: true, rows: 2 },
        { name: 'notes', label: 'Internal notes', type: 'textarea', full: true, rows: 2 },
      ]}
      columns={[
        { key: 'hearing_at', label: 'Date', strong: true, render: (r) => fmtDateTime(r.hearing_at) },
        { key: 'case', label: 'Case', render: (r) => <Link to={`/dashboard/cases/${r.case}`}>{caseLabel(cases, r.case)}</Link> },
        { key: 'court_name', label: 'Court' },
        { key: 'outcome', label: 'Outcome', render: (r) => r.outcome || <span className="muted">Pending</span> },
        { key: 'next_hearing_date', label: 'Next', render: (r) => fmtDate(r.next_hearing_date) },
      ]} />
  );
}

/* ---------------- Tasks ---------------- */
export function Tasks({ caseId }) {
  const { cases, users } = useLookups(['cases', 'users']);
  const { user } = useAuth();
  const [mine, setMine] = useState(false);
  const firmUsers = users.filter((u) => u.role !== 'client' && u.is_active);
  return (
    <ResourceManager title="Tasks" endpoint="/api/tasks/" listPath={mine ? '/api/tasks/my-tasks/' : '/api/tasks/'} createLabel="New task"
      baseQuery={caseId ? { case: caseId } : {}} defaults={{ case: caseId, assigned_to: user?.id, due_date: todayISO() }} canDelete={() => true}
      headExtra={!caseId && (
        <div className="tabs mb-0" style={{ padding: 3 }}>
          <button type="button" className={!mine ? 'on' : ''} onClick={() => setMine(false)}>All tasks</button>
          <button type="button" className={mine ? 'on' : ''} onClick={() => setMine(true)}>My tasks</button>
        </div>
      )}
      fields={[
        { name: 'title', label: 'Title', required: true, full: true },
        { name: 'case', label: 'Case (optional)', type: 'select', nullable: true, lockOnEdit: true, hidden: !!caseId, options: opts(cases, (c) => `${c.case_number} — ${c.title}`) },
        { name: 'assigned_to', label: 'Assign to', type: 'select', required: true, options: opts(firmUsers, (u) => `${u.full_name} (${u.role})`) },
        { name: 'due_date', label: 'Due date', type: 'date', required: true },
        { name: 'priority', label: 'Priority', type: 'select', options: choice('low', 'normal', 'high'), default: 'normal' },
        { name: 'status', label: 'Status', type: 'select', options: choice('pending', 'in_progress', 'completed', 'cancelled'), default: 'pending' },
        { name: 'description', label: 'Description', type: 'textarea', full: true, rows: 3 },
      ]}
      columns={[
        { key: 'title', label: 'Task', strong: true },
        { key: 'case', label: 'Case', render: (r) => (r.case ? <Link to={`/dashboard/cases/${r.case}`}>{caseLabel(cases, r.case)}</Link> : <span className="muted">Standalone</span>) },
        { key: 'assigned_to', label: 'Assignee', render: (r) => userName(users, r.assigned_to) },
        { key: 'due_date', label: 'Due', render: (r) => <span style={r.due_date < todayISO() && !['completed', 'cancelled'].includes(r.status) ? { color: 'var(--red)', fontWeight: 700 } : undefined}>{fmtDate(r.due_date)}</span> },
        { key: 'priority', label: 'Priority', render: (r) => <Badge value={r.priority} /> },
        { key: 'status', label: 'Status', render: (r) => <Badge value={r.status} /> },
      ]}
      rowActions={(r, reload) => r.status !== 'completed' && (
        <button type="button" className="icon-btn" title="Mark completed" onClick={async () => { await api.patch(`/api/tasks/${r.id}/`, { status: 'completed' }); reload(); }}><i className="bi bi-check2" /></button>
      )} />
  );
}

/* ---------------- Documents ---------------- */
export function Documents({ caseId }) {
  const { cases, users } = useLookups(['cases', 'users']);
  const toast = useToast();
  return (
    <ResourceManager title="Documents" endpoint="/api/documents/" createLabel="Upload document" multipart
      baseQuery={caseId ? { case: caseId } : {}} defaults={{ case: caseId, version: 1 }}
      fields={[
        { name: 'case', label: 'Case', type: 'select', required: true, lockOnEdit: true, hidden: !!caseId, options: opts(cases, (c) => `${c.case_number} — ${c.title}`) },
        { name: 'title', label: 'Title', required: true },
        { name: 'document_type', label: 'Document type', required: true, placeholder: 'e.g. petition, evidence, deed' },
        { name: 'version', label: 'Version', type: 'number', min: 1, default: 1 },
        { name: 'file', label: 'File (PDF, PNG, JPG or TXT · max 10 MB)', type: 'file', required: true, createOnly: true, full: true },
        { name: 'is_client_visible', label: 'Visible to client in portal', type: 'checkbox', full: true },
      ]}
      transform={(payload, values, isEdit) => {
        if (caseId && payload instanceof FormData && !payload.get('case')) payload.append('case', caseId);
        if (isEdit && !(payload instanceof FormData)) delete payload.file;
        return payload;
      }}
      columns={[
        { key: 'title', label: 'Title', strong: true, render: (r) => <><i className="bi bi-file-earmark-text" style={{ color: 'var(--sage-500)' }} /> {r.title}</> },
        { key: 'case', label: 'Case', render: (r) => <Link to={`/dashboard/cases/${r.case}`}>{caseLabel(cases, r.case)}</Link> },
        { key: 'document_type', label: 'Type', render: (r) => label(r.document_type) },
        { key: 'version', label: 'Ver.', render: (r) => `v${r.version}` },
        { key: 'is_client_visible', label: 'Client', render: (r) => (r.is_client_visible ? <Badge tone="green">Shared</Badge> : <Badge tone="grey">Private</Badge>) },
        { key: 'uploaded_by', label: 'Uploaded', render: (r) => <>{fmtDate(r.uploaded_at)}<div className="small muted">{userName(users, r.uploaded_by)}</div></> },
      ]}
      rowActions={(r) => (
        <button type="button" className="icon-btn" title="Download" onClick={() => downloadFile(r.download_url, r.title).catch((e) => toast.error(e.message))}><i className="bi bi-download" /></button>
      )} />
  );
}

/* ---------------- Invoices & payments ---------------- */
export function invoiceFields(clients, cases) {
  return [
    { name: 'invoice_number', label: 'Invoice number', required: true },
    { name: 'client', label: 'Client', type: 'select', required: true, lockOnEdit: true, options: opts(clients, 'full_name'), onChangeReset: ['case'] },
    { name: 'case', label: 'Case (optional)', type: 'select', nullable: true, options: (v) => opts(cases.filter((c) => !v.client || String(c.client) === String(v.client)), (c) => `${c.case_number} — ${c.title}`) },
    { name: 'amount', label: 'Amount (BDT)', type: 'number', min: '0.01', step: '0.01', required: true },
    { name: 'issue_date', label: 'Issue date', type: 'date', required: true },
    { name: 'due_date', label: 'Due date', type: 'date', required: true },
    { name: 'description', label: 'Description', type: 'textarea', full: true, rows: 2 },
  ];
}

export function PaymentModalButton({ invoice, onDone }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" className="btn btn-xs btn-outline" onClick={() => setOpen(true)}><i className="bi bi-cash" /> Pay</button>
      {open && <PaymentForm invoice={invoice} onClose={() => setOpen(false)} onSaved={() => { setOpen(false); onDone(); }} />}
    </>
  );
}

function PaymentForm({ invoice, onClose, onSaved }) {
  return (
    <FormModalLazy title={`Record payment · ${invoice.invoice_number}`} endpoint="/api/payments/" onClose={onClose} onSaved={onSaved}
      defaults={{ invoice: invoice.id, amount: invoice.balance, date: todayISO(), method: 'cash' }}
      fields={[
        { name: 'invoice', label: 'Invoice', type: 'select', required: true, readOnly: false, hidden: true, options: [{ value: invoice.id, label: invoice.invoice_number }] },
        { name: 'amount', label: `Amount (balance ${money(invoice.balance)})`, type: 'number', min: '0.01', step: '0.01', required: true },
        { name: 'method', label: 'Method', type: 'select', required: true, options: choice('cash', 'bank', 'mobile_banking') },
        { name: 'date', label: 'Date', type: 'date', required: true },
        { name: 'reference', label: 'Reference / transaction ID', full: true },
      ]} />
  );
}


export function Invoices({ caseId, clientId }) {
  const { clients, cases } = useLookups(['clients', 'cases']);
  return (
    <ResourceManager title="Invoices" endpoint="/api/invoices/" createLabel="New invoice"
      baseQuery={caseId ? { case: caseId } : {}} defaults={{ case: caseId, client: clientId, issue_date: todayISO() }}
      filters={caseId ? [] : [{ name: 'client', label: 'All clients', options: opts(clients, 'full_name') }]}
      fields={invoiceFields(clients, cases)} canDelete={(r) => Number(r.paid_amount) === 0}
      onMutate={() => invalidateLookup('invoices')}
      columns={[
        { key: 'invoice_number', label: 'Invoice', strong: true },
        { key: 'client', label: 'Client', render: (r) => clientName(clients, r.client) },
        { key: 'case', label: 'Case', render: (r) => (r.case ? <Link to={`/dashboard/cases/${r.case}`}>{caseLabel(cases, r.case)}</Link> : '—') },
        { key: 'amount', label: 'Amount', render: (r) => money(r.amount) },
        { key: 'balance', label: 'Balance', render: (r) => <b>{money(r.balance)}</b> },
        { key: 'due_date', label: 'Due', render: (r) => fmtDate(r.due_date) },
        { key: 'status', label: 'Status', render: (r) => <Badge value={r.status} /> },
      ]}
      rowActions={(r, reload) => Number(r.balance) > 0 && <PaymentModalButton invoice={r} onDone={reload} />} />
  );
}

export function Payments() {
  const { invoices } = useLookups(['invoices']);
  const { users } = useLookups(['users']);
  return (
    <ResourceManager title="Payments" endpoint="/api/payments/" createLabel="Record payment" canDelete={() => true}
      filters={[{ name: 'invoice', label: 'All invoices', options: opts(invoices, 'invoice_number') }]}
      defaults={{ date: todayISO(), method: 'cash' }}
      fields={[
        { name: 'invoice', label: 'Invoice', type: 'select', required: true, lockOnEdit: true, options: opts(invoices, (i) => `${i.invoice_number} — balance ${money(i.balance)}`) },
        { name: 'amount', label: 'Amount (BDT)', type: 'number', min: '0.01', step: '0.01', required: true },
        { name: 'method', label: 'Method', type: 'select', required: true, options: choice('cash', 'bank', 'mobile_banking') },
        { name: 'date', label: 'Date', type: 'date', required: true },
        { name: 'reference', label: 'Reference', full: true },
      ]}
      onMutate={() => invalidateLookup('invoices')}
      columns={[
        { key: 'date', label: 'Date', strong: true, render: (r) => fmtDate(r.date) },
        { key: 'invoice', label: 'Invoice', render: (r) => byId(invoices, r.invoice)?.invoice_number || `#${r.invoice}` },
        { key: 'amount', label: 'Amount', render: (r) => <b>{money(r.amount)}</b> },
        { key: 'method', label: 'Method', render: (r) => label(r.method) },
        { key: 'reference', label: 'Reference', render: (r) => r.reference || '—' },
        { key: 'recorded_by', label: 'Recorded by', render: (r) => userName(users, r.recorded_by) },
      ]} />
  );
}

/* ---------------- Users (admin) ---------------- */
export function Users() {
  const { user: me } = useAuth();
  return (
    <ResourceManager title="User accounts" endpoint="/api/users/" createLabel="New account"
      filters={[{ name: 'search', type: 'search', label: 'Search users…' }, { name: 'role', label: 'All roles', options: choice('admin', 'lawyer', 'staff', 'client') }]}
      onMutate={() => invalidateLookup('users')}
      fields={(row) => [
        { name: 'username', label: 'Username', required: true, lockOnEdit: true },
        { name: 'role', label: 'Role', type: 'select', required: true, options: choice('client', 'lawyer', 'staff', 'admin'), default: 'client', lockOnEdit: row?.id === me?.id },
        { name: 'first_name', label: 'First name' },
        { name: 'last_name', label: 'Last name' },
        { name: 'email', label: 'Email', type: 'email' },
        { name: 'phone', label: 'Phone' },
        { name: 'password', label: row ? 'New password (leave blank to keep)' : 'Initial password', type: 'password', required: !row, omitEmpty: true, hint: 'At least 8 characters; avoid common or numeric-only passwords.' },
        { name: 'is_active', label: 'Account active', type: 'checkbox', default: true, hidden: row?.id === me?.id },
      ]}
      columns={[
        { key: 'full_name', label: 'Name', strong: true, render: (r) => <div>{r.full_name}<div className="small muted">@{r.username}</div></div> },
        { key: 'role', label: 'Role', render: (r) => <Badge value={r.role} /> },
        { key: 'email', label: 'Email', render: (r) => r.email || '—' },
        { key: 'is_active', label: 'Status', render: (r) => (r.is_active ? <Badge tone="green">Active</Badge> : <Badge tone="grey">Inactive</Badge>) },
        { key: 'has_client_record', label: 'Client record', render: (r) => (r.role === 'client' ? (r.has_client_record ? 'Linked' : <span className="muted">Not linked</span>) : '—') },
        { key: 'last_login', label: 'Last login', render: (r) => fmtDateTime(r.last_login) },
      ]} />
  );
}
