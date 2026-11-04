import { useState } from 'react';
import { Link } from 'react-router-dom';
import { downloadFile } from '../../api/client';
import { Badge, Empty, ErrorBox, Pagination, Spinner } from '../../components/UI';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { fmtDate, fmtDateTime, fmtTime, label, money } from '../../utils/format';
import { useFetch } from '../../utils/hooks';

function PortalList({ path, title, columns, empty, icon, actions }) {
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useFetch(`${path}${page > 1 ? `?page=${page}` : ''}`);
  const rows = data?.results || [];
  return (
    <div className="panel">
      <div className="panel-head"><h3>{title}</h3><button type="button" className="icon-btn" onClick={reload}><i className="bi bi-arrow-clockwise" /></button></div>
      {error && <div className="panel-body"><ErrorBox error={error} onRetry={reload} /></div>}
      {loading && !data ? <Spinner /> : rows.length === 0 ? <Empty icon={icon} title={empty} /> : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr>{columns.map((c) => <th key={c.key}>{c.label}</th>)}{actions && <th />}</tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.id}>
                {columns.map((c) => <td key={c.key} className={c.strong ? 'strong' : undefined}>{c.render ? c.render(r) : r[c.key] ?? '—'}</td>)}
                {actions && <td><div className="actions">{actions(r)}</div></td>}
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      <Pagination data={data} page={page} setPage={setPage} />
    </div>
  );
}

export function PortalHome() {
  const { user } = useAuth();
  const { data: s, loading, error } = useFetch('/api/portal/summary/');
  const hearings = useFetch('/api/portal/hearings/');
  const docs = useFetch('/api/portal/documents/');
  const me = useFetch('/api/clients/');
  const lawyerName = me.data?.results?.[0]?.assigned_lawyer_name;
  if (loading) return <Spinner />;
  if (error) return <ErrorBox error={error} />;
  const stats = [
    ['bi-briefcase', s.active_cases, `Active cases (of ${s.cases})`, '/portal/cases'],
    ['bi-bank', s.upcoming_hearings, 'Upcoming hearings', '/portal/hearings'],
    ['bi-calendar2-week', s.upcoming_appointments, 'Upcoming appointments', '/portal/appointments'],
    ['bi-wallet2', money(s.outstanding_balance), `Outstanding · ${s.invoices} invoices`, '/portal/invoices'],
  ];
  return (
    <div className="stack">
      <div className="panel panel-body" style={{ background: 'linear-gradient(120deg, var(--forest-600), var(--forest-800))', color: 'var(--cream)', border: 0 }}>
        <h2 style={{ color: 'var(--cream)', marginBottom: 4 }}>Welcome, {user.first_name || user.username}</h2>
        <p className="mb-0" style={{ color: 'rgba(246,241,228,.8)' }}>Follow your matters with Anadi Law Firm — shared updates, hearings, documents and invoices.</p>
        {lawyerName && <p className="mb-0 mt-2" style={{ color: 'var(--sage-300)' }}><i className="bi bi-person-badge" /> Your lawyer: <b style={{ color: 'var(--cream)' }}>{lawyerName}</b></p>}
      </div>
      <div className="stat-grid">
        {stats.map(([icon, v, t, to]) => (
          <Link key={t} to={to} style={{ color: 'inherit' }}>
            <div className="stat card-hover"><div className="icon-badge"><i className={`bi ${icon}`} /></div><div><strong style={{ fontSize: typeof v === 'string' ? '1.4rem' : undefined }}>{v}</strong><span>{t}</span></div></div>
          </Link>
        ))}
      </div>
      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <div className="panel">
          <div className="panel-head"><h3>Next hearings</h3><Link className="small" to="/portal/hearings">View all</Link></div>
          <div className="panel-body">
            {(hearings.data?.results || []).length === 0 ? <Empty icon="bi-bank" title="No upcoming hearings" /> : hearings.data.results.slice(0, 4).map((h) => {
              const d = new Date(h.hearing_at);
              return (
                <div key={h.id} className="list-item">
                  <div className="date-tile"><b>{d.getDate()}</b><small>{d.toLocaleString('en', { month: 'short' })}</small></div>
                  <div><div className="strong">{h.court_name}</div><div className="small muted">{fmtTime(h.hearing_at)}{h.case_number ? ` · ${h.case_number}` : ''}</div></div>
                </div>
              );
            })}
          </div>
        </div>
        <div className="panel">
          <div className="panel-head"><h3>Recent documents</h3><Link className="small" to="/portal/documents">View all</Link></div>
          <div className="panel-body">
            {(docs.data?.results || []).length === 0 ? <Empty icon="bi-folder2" title="No shared documents yet" /> : docs.data.results.slice(0, 4).map((d) => (
              <div key={d.id} className="list-item">
                <i className="bi bi-file-earmark-text" style={{ color: 'var(--sage-500)', fontSize: '1.3rem' }} />
                <div style={{ flex: 1 }}><div className="strong">{d.title}</div><div className="small muted">{label(d.document_type)} · v{d.version} · {fmtDate(d.uploaded_at)}</div></div>
                <button type="button" className="icon-btn" onClick={() => downloadFile(d.download_url, d.title)}><i className="bi bi-download" /></button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function SharedNotes({ caseId }) {
  const { data, loading } = useFetch(`/api/case-notes/?case=${caseId}`);
  if (loading) return <Spinner small />;
  const notes = data?.results || [];
  if (!notes.length) return <p className="small muted mb-0">No shared updates yet.</p>;
  return notes.map((n) => (
    <div key={n.id} className="note"><div className="note-meta"><span>{fmtDateTime(n.created_at)}</span></div><div style={{ whiteSpace: 'pre-wrap' }}>{n.body}</div></div>
  ));
}

export function PortalCases() {
  const { data, loading, error } = useFetch('/api/portal/cases/');
  const [open, setOpen] = useState(null);
  if (loading) return <Spinner />;
  if (error) return <ErrorBox error={error} />;
  const cases = data?.results || [];
  if (!cases.length) return <div className="panel"><Empty icon="bi-briefcase" title="No cases yet" /></div>;
  return (
    <div className="stack">
      {cases.map((c) => (
        <div key={c.id} className="panel">
          <div className="panel-head">
            <div>
              <div className="flex"><span className="chip">{c.case_number}</span><Badge value={c.status} /></div>
              <h3 style={{ marginTop: 8 }}>{c.title}</h3>
            </div>
            <button type="button" className="btn btn-outline btn-sm" onClick={() => setOpen(open === c.id ? null : c.id)}>
              {open === c.id ? 'Hide updates' : 'Show updates'} <i className={`bi bi-chevron-${open === c.id ? 'up' : 'down'}`} />
            </button>
          </div>
          <div className="panel-body">
            <div className="kv">
              <div><span>Court</span><b>{c.court || '—'}</b></div>
              <div><span>Lead lawyer</span><b>{c.lead_lawyers.map((l) => l.name).join(', ') || '—'}</b></div>
              <div><span>Filing date</span><b>{fmtDate(c.filing_date)}</b></div>
            </div>
            {c.description && <p className="mt-2 mb-0 muted" style={{ whiteSpace: 'pre-wrap' }}>{c.description}</p>}
            {open === c.id && <div className="mt-3"><h4>Shared updates</h4><SharedNotes caseId={c.id} /></div>}
          </div>
        </div>
      ))}
    </div>
  );
}

export const PortalHearings = () => (
  <PortalList path="/api/portal/hearings/" title="Upcoming hearings" icon="bi-bank" empty="No upcoming hearings"
    columns={[
      { key: 'hearing_at', label: 'Date & time', strong: true, render: (r) => fmtDateTime(r.hearing_at) },
      { key: 'court_name', label: 'Court' },
      { key: 'case_number', label: 'Court case no.', render: (r) => r.case_number || '—' },
      { key: 'outcome', label: 'Outcome', render: (r) => r.outcome || <span className="muted">Pending</span> },
      { key: 'next_hearing_date', label: 'Next hearing', render: (r) => fmtDate(r.next_hearing_date) },
    ]} />
);

export const PortalAppointments = () => (
  <PortalList path="/api/portal/appointments/" title="Appointments" icon="bi-calendar2" empty="No appointments"
    columns={[
      { key: 'start', label: 'When', strong: true, render: (r) => fmtDateTime(r.start) },
      { key: 'lawyer_name', label: 'Lawyer' },
      { key: 'appointment_type', label: 'Type', render: (r) => label(r.appointment_type) },
      { key: 'status', label: 'Status', render: (r) => <Badge value={r.status} /> },
    ]} />
);

export function PortalDocuments() {
  const toast = useToast();
  return (
    <PortalList path="/api/portal/documents/" title="Shared documents" icon="bi-folder2" empty="No shared documents yet"
      columns={[
        { key: 'title', label: 'Title', strong: true, render: (r) => <><i className="bi bi-file-earmark-text" style={{ color: 'var(--sage-500)' }} /> {r.title}</> },
        { key: 'document_type', label: 'Type', render: (r) => label(r.document_type) },
        { key: 'version', label: 'Version', render: (r) => `v${r.version}` },
        { key: 'uploaded_at', label: 'Uploaded', render: (r) => fmtDate(r.uploaded_at) },
      ]}
      actions={(r) => <button type="button" className="btn btn-xs btn-outline" onClick={() => downloadFile(r.download_url, r.title).catch((e) => toast.error(e.message))}><i className="bi bi-download" /> Download</button>} />
  );
}

export const PortalInvoices = () => (
  <PortalList path="/api/portal/invoices/" title="Invoices" icon="bi-receipt" empty="No invoices"
    columns={[
      { key: 'invoice_number', label: 'Invoice', strong: true },
      { key: 'issue_date', label: 'Issued', render: (r) => fmtDate(r.issue_date) },
      { key: 'due_date', label: 'Due', render: (r) => fmtDate(r.due_date) },
      { key: 'description', label: 'Description', render: (r) => r.description || '—' },
      { key: 'amount', label: 'Amount', render: (r) => money(r.amount) },
      { key: 'paid_amount', label: 'Paid', render: (r) => money(r.paid_amount) },
      { key: 'balance', label: 'Balance', render: (r) => <b>{money(r.balance)}</b> },
      { key: 'status', label: 'Status', render: (r) => <Badge value={r.status} /> },
    ]} />
);
