import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../../api/client';
import ResourceManager, { FormModal } from '../../components/ResourceManager';
import { Badge, Confirm, Empty, ErrorBox, Field, Spinner } from '../../components/UI';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { fmtDate, fmtDateTime, label } from '../../utils/format';
import { byId, invalidateLookup, useFetch, useLookups } from '../../utils/hooks';
import { Appointments, Documents, Hearings, Invoices, Tasks, choice, opts } from './Resources';

export function caseFields(clients, areas, isEdit) {
  return [
    { name: 'case_number', label: 'Case number', required: true },
    { name: 'title', label: 'Title', required: true },
    { name: 'client', label: 'Client', type: 'select', required: true, lockOnEdit: true, options: opts(clients.filter((c) => isEdit || c.status === 'active'), 'full_name') },
    { name: 'practice_area', label: 'Practice area', type: 'select', required: true, options: opts(areas) },
    { name: 'status', label: 'Status', type: 'select', options: choice('open', 'in_progress', 'on_hold', 'closed', 'archived'), default: 'open' },
    { name: 'priority', label: 'Priority', type: 'select', options: choice('low', 'normal', 'high'), default: 'normal' },
    { name: 'court', label: 'Court' },
    { name: 'opposite_party', label: 'Opposite party' },
    { name: 'filing_date', label: 'Filing date', type: 'date', nullable: true },
    { name: 'closed_date', label: 'Closed date', type: 'date', nullable: true, hint: 'Only for closed/archived cases' },
    { name: 'description', label: 'Client-visible summary', type: 'textarea', full: true, hint: 'Visible to the client in the portal. Use internal notes for confidential discussion.' },
  ];
}

export default function Cases() {
  const navigate = useNavigate();
  const { hasRole } = useAuth();
  const { clients, practiceAreas, users } = useLookups(['clients', 'practiceAreas', 'users']);
  return (
    <ResourceManager title="Cases" endpoint="/api/cases/" createLabel="New case"
      canCreate={hasRole('admin', 'staff')} canEdit={() => false}
      fields={caseFields(clients, practiceAreas, false)}
      onMutate={() => invalidateLookup('cases')}
      onRowClick={(r) => navigate(`/dashboard/cases/${r.id}`)}
      filters={[
        { name: 'search', type: 'search', label: 'Search number or title…' },
        { name: 'status', label: 'All statuses', options: choice('open', 'in_progress', 'on_hold', 'closed', 'archived') },
        { name: 'practice_area', label: 'All areas', options: opts(practiceAreas) },
        { name: 'lawyer', label: 'All lawyers', options: opts(users.filter((u) => u.role === 'lawyer'), 'full_name') },
        { name: 'ordering', label: 'Newest first', options: [{ value: 'created_at', label: 'Oldest first' }, { value: '-filing_date', label: 'Filing date' }, { value: 'case_number', label: 'Case number' }] },
      ]}
      columns={[
        { key: 'case_number', label: 'Case', strong: true, render: (r) => <div>{r.case_number}<div className="small muted" style={{ fontWeight: 500 }}>{r.title}</div></div> },
        { key: 'client', label: 'Client', render: (r) => byId(clients, r.client)?.full_name || `#${r.client}` },
        { key: 'practice_area', label: 'Area', render: (r) => byId(practiceAreas, r.practice_area)?.name || '—' },
        { key: 'lead_lawyers', label: 'Lead', render: (r) => r.lead_lawyers.map((l) => l.name).join(', ') || <span className="muted">Unassigned</span> },
        { key: 'priority', label: 'Priority', render: (r) => <Badge value={r.priority} /> },
        { key: 'status', label: 'Status', render: (r) => <Badge value={r.status} /> },
      ]}
      rowActions={(r) => <Link className="icon-btn" to={`/dashboard/cases/${r.id}`} title="Open"><i className="bi bi-arrow-right" /></Link>} />
  );
}

function Notes({ caseId }) {
  const toast = useToast();
  const { users } = useLookups(['users']);
  const { data, loading, reload } = useFetch(`/api/case-notes/?case=${caseId}`);
  const [body, setBody] = useState('');
  const [shared, setShared] = useState(false);
  const [busy, setBusy] = useState(false);
  const add = async (e) => {
    e.preventDefault();
    if (!body.trim()) return;
    setBusy(true);
    try {
      await api.post('/api/case-notes/', { case: caseId, body, is_internal: !shared });
      setBody(''); setShared(false); toast.success('Note added'); reload();
    } catch (err) { toast.error(err.message); } finally { setBusy(false); }
  };
  return (
    <div className="grid grid-2" style={{ alignItems: 'start' }}>
      <form className="panel panel-body stack" onSubmit={add}>
        <h3 className="mb-0">Add a note</h3>
        <Field type="textarea" name="note" label="Note" value={body} onChange={setBody} hint="Notes are permanent. Correct a note by adding a new one." />
        <Field type="checkbox" name="shared" label="Share with client (visible in portal)" value={shared} onChange={setShared} />
        <button className="btn btn-primary" disabled={busy || !body.trim()}>{busy ? <Spinner small /> : 'Add note'}</button>
      </form>
      <div>
        {loading ? <Spinner /> : (data?.results || []).length === 0 ? <Empty icon="bi-sticky" title="No notes yet" /> : data.results.map((n) => (
          <div key={n.id} className={`note${n.is_internal ? ' internal' : ''}`}>
            <div className="note-meta">
              <span><b>{byId(users, n.author)?.full_name || 'Staff'}</b> · {fmtDateTime(n.created_at)}</span>
              {n.is_internal ? <Badge tone="amber">Internal</Badge> : <Badge tone="green">Shared</Badge>}
            </div>
            <div style={{ whiteSpace: 'pre-wrap' }}>{n.body}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Assignments({ caseId, canManage, onChange }) {
  const toast = useToast();
  const { users } = useLookups(['users']);
  const { data, loading, reload } = useFetch(`/api/case-assignments/?case=${caseId}`);
  const [form, setForm] = useState({ user: '', role: 'lead' });
  const [removing, setRemoving] = useState(null);
  const [busy, setBusy] = useState(false);
  const add = async (e) => {
    e.preventDefault(); setBusy(true);
    try { await api.post('/api/case-assignments/', { case: caseId, user: form.user, role: form.role }); toast.success('Team member assigned'); setForm({ user: '', role: 'lead' }); reload(); invalidateLookup('cases'); onChange?.(); } catch (err) { toast.error(err.message); } finally { setBusy(false); }
  };
  const remove = async () => {
    setBusy(true);
    try { await api.del(`/api/case-assignments/${removing.id}/`); toast.success('Assignment removed'); setRemoving(null); reload(); onChange?.(); } catch (err) { toast.error(err.message); } finally { setBusy(false); }
  };
  const assigned = new Set((data?.results || []).map((a) => a.user));
  return (
    <div className="panel">
      <div className="panel-head"><h3>Case team</h3></div>
      {canManage && (
        <form className="panel-body toolbar" onSubmit={add} style={{ borderBottom: '1px solid var(--line)' }}>
          <select className="input" value={form.user} onChange={(e) => setForm((f) => ({ ...f, user: e.target.value }))} required>
            <option value="">Choose lawyer or staff…</option>
            {users.filter((u) => ['lawyer', 'staff'].includes(u.role) && u.is_active && !assigned.has(u.id)).map((u) => <option key={u.id} value={u.id}>{u.full_name} ({u.role})</option>)}
          </select>
          <select className="input" value={form.role} onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}>
            <option value="lead">Lead</option><option value="support">Support</option>
          </select>
          <button className="btn btn-primary btn-sm" disabled={busy || !form.user}><i className="bi bi-person-plus" /> Assign</button>
        </form>
      )}
      {loading ? <Spinner /> : (data?.results || []).length === 0 ? <Empty icon="bi-people" title="No one assigned yet" /> : (
        <table className="table">
          <thead><tr><th>Member</th><th>Role on case</th><th>Assigned</th><th /></tr></thead>
          <tbody>{data.results.map((a) => {
            const u = byId(users, a.user);
            return (
              <tr key={a.id}>
                <td className="strong">{u?.full_name || `#${a.user}`} <span className="small muted">({u?.role})</span></td>
                <td><Badge value={a.role} /></td>
                <td>{fmtDate(a.assigned_at)}</td>
                <td><div className="actions">{canManage && <button type="button" className="icon-btn danger" onClick={() => setRemoving(a)}><i className="bi bi-x-lg" /></button>}</div></td>
              </tr>
            );
          })}</tbody>
        </table>
      )}
      {removing && <Confirm danger title="Remove assignment" message="Remove this member from the case? Lawyers lose access to unassigned cases." confirmText="Remove" busy={busy} onConfirm={remove} onClose={() => setRemoving(null)} />}
    </div>
  );
}

const TABS = [['notes', 'Notes', 'bi-sticky'], ['team', 'Team', 'bi-people'], ['hearings', 'Hearings', 'bi-bank'], ['tasks', 'Tasks', 'bi-check2-square'],
  ['documents', 'Documents', 'bi-folder2'], ['appointments', 'Appointments', 'bi-calendar2-week'], ['invoices', 'Invoices', 'bi-receipt']];

export function CaseDetail() {
  const { id } = useParams();
  const { hasRole } = useAuth();
  const { clients, practiceAreas } = useLookups(['clients', 'practiceAreas']);
  const { data: c, loading, error, reload } = useFetch(`/api/cases/${id}/`);
  const [tab, setTab] = useState('notes');
  const [editing, setEditing] = useState(false);

  if (loading && !c) return <Spinner />;
  if (error) return <ErrorBox error={error} />;
  const client = byId(clients, c.client);

  return (
    <div className="stack">
      <Link to="/dashboard/cases" className="small"><i className="bi bi-arrow-left" /> All cases</Link>
      <div className="panel">
        <div className="panel-head">
          <div>
            <div className="flex flex-wrap"><span className="chip">{c.case_number}</span><Badge value={c.status} /><Badge value={c.priority}>{label(c.priority)} priority</Badge></div>
            <h2 style={{ margin: '10px 0 0' }}>{c.title}</h2>
          </div>
          <button type="button" className="btn btn-outline btn-sm" onClick={() => setEditing(true)}><i className="bi bi-pencil" /> Edit case</button>
        </div>
        <div className="panel-body">
          <div className="kv">
            <div><span>Client</span><b>{client?.full_name || `#${c.client}`}</b></div>
            <div><span>Practice area</span><b>{byId(practiceAreas, c.practice_area)?.name || '—'}</b></div>
            <div><span>Lead lawyer(s)</span><b>{c.lead_lawyers.map((l) => l.name).join(', ') || '—'}</b></div>
            <div><span>Court</span><b>{c.court || '—'}</b></div>
            <div><span>Opposite party</span><b>{c.opposite_party || '—'}</b></div>
            <div><span>Filed / closed</span><b>{fmtDate(c.filing_date)} / {fmtDate(c.closed_date)}</b></div>
          </div>
          {c.description && <p className="mt-2 mb-0" style={{ whiteSpace: 'pre-wrap', color: 'var(--ink-soft)' }}>{c.description}</p>}
        </div>
      </div>

      <div className="tabs">
        {TABS.map(([k, v, icon]) => <button key={k} type="button" className={tab === k ? 'on' : ''} onClick={() => setTab(k)}><i className={`bi ${icon}`} /> {v}</button>)}
      </div>
      {tab === 'notes' && <Notes caseId={c.id} />}
      {tab === 'team' && <Assignments caseId={c.id} canManage={hasRole('admin', 'staff')} onChange={reload} />}
      {tab === 'hearings' && <Hearings caseId={c.id} />}
      {tab === 'tasks' && <Tasks caseId={c.id} />}
      {tab === 'documents' && <Documents caseId={c.id} />}
      {tab === 'appointments' && <Appointments caseId={c.id} clientId={c.client} />}
      {tab === 'invoices' && <Invoices caseId={c.id} clientId={c.client} />}

      {editing && (
        <FormModal title="Edit case" endpoint="/api/cases/" row={c} fields={caseFields(clients, practiceAreas, true)}
          onClose={() => setEditing(false)} onSaved={() => { setEditing(false); invalidateLookup('cases'); reload(); }} />
      )}
    </div>
  );
}
