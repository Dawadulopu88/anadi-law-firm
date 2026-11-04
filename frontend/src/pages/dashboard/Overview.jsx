import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getAll } from '../../api/client';
import { Badge, Empty, Spinner } from '../../components/UI';
import { useAuth } from '../../context/AuthContext';
import { fmtDate, fmtDateTime, fmtTime, label, money, todayISO } from '../../utils/format';
import { byId, useFetch, useLookups } from '../../utils/hooks';

function Stat({ icon, value, text, tone, to }) {
  const body = (
    <div className="stat card-hover">
      <div className={`icon-badge${tone === 'brass' ? ' brass' : ''}`}><i className={`bi ${icon}`} /></div>
      <div><strong>{value ?? '—'}</strong><span>{text}</span></div>
    </div>
  );
  return to ? <Link to={to} style={{ color: 'inherit' }}>{body}</Link> : body;
}

export default function Overview() {
  const { user } = useAuth();
  const { cases: caseList, clients } = useLookups(['cases', 'clients']);
  const hearings = useFetch('/api/hearings/upcoming/');
  const tasks = useFetch('/api/tasks/my-tasks/');
  const consultations = useFetch('/api/consultations/?status=new');
  const appts = useFetch('/api/appointments/?status=scheduled');
  const [finance, setFinance] = useState(null);

  useEffect(() => {
    getAll('/api/invoices/').then((list) => setFinance({
      outstanding: list.reduce((s, i) => s + Number(i.balance || 0), 0),
      unpaid: list.filter((i) => i.status !== 'paid').length,
    })).catch(() => setFinance({ outstanding: 0, unpaid: 0 }));
  }, []);

  const active = caseList.filter((c) => !['closed', 'archived'].includes(c.status)).length;
  const openTasks = (tasks.data?.results || []).filter((t) => !['completed', 'cancelled'].includes(t.status));
  const upcomingAppts = (appts.data?.results || []).filter((a) => new Date(a.end) > new Date()).slice(0, 5);
  const hour = new Date().getHours();
  const greet = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  return (
    <div className="stack">
      <div className="flex between flex-wrap">
        <div>
          <h2 className="mb-0">{greet}, {user.first_name || user.username}</h2>
          <p className="muted mb-0">Here is what needs your attention today, {fmtDate(todayISO())}.</p>
        </div>
        <div className="flex">
          <Link to="/dashboard/cases" className="btn btn-outline btn-sm"><i className="bi bi-briefcase" /> Cases</Link>
          <Link to="/dashboard/appointments" className="btn btn-primary btn-sm"><i className="bi bi-calendar-plus" /> Schedule</Link>
        </div>
      </div>

      <div className="stat-grid">
        <Stat icon="bi-briefcase" value={active} text="Active cases" to="/dashboard/cases" />
        <Stat icon="bi-bank" value={hearings.data?.count} text="Upcoming hearings" to="/dashboard/hearings" />
        <Stat icon="bi-chat-square-text" value={consultations.data?.count} text="New consultations" to="/dashboard/consultations" tone="brass" />
        <Stat icon="bi-cash-stack" value={finance ? money(finance.outstanding).replace('.00', '') : null} text={`Outstanding · ${finance?.unpaid ?? '—'} invoices`} to="/dashboard/invoices" />
      </div>

      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <div className="panel">
          <div className="panel-head"><h3>Upcoming hearings</h3><Link to="/dashboard/hearings" className="small">View all</Link></div>
          <div className="panel-body">
            {hearings.loading ? <Spinner /> : (hearings.data?.results || []).length === 0 ? <Empty icon="bi-bank" title="No upcoming hearings" /> : hearings.data.results.slice(0, 5).map((h) => {
              const d = new Date(h.hearing_at);
              return (
                <div key={h.id} className="list-item">
                  <div className="date-tile"><b>{d.getDate()}</b><small>{d.toLocaleString('en', { month: 'short' })}</small></div>
                  <div style={{ flex: 1 }}>
                    <Link to={`/dashboard/cases/${h.case}`} className="strong">{byId(caseList, h.case)?.case_number || `Case #${h.case}`}</Link>
                    <div className="small muted">{h.court_name} · {fmtTime(h.hearing_at)}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head"><h3>My open tasks</h3><Link to="/dashboard/tasks" className="small">View all</Link></div>
          <div className="panel-body">
            {tasks.loading ? <Spinner /> : openTasks.length === 0 ? <Empty icon="bi-check2-all" title="You're all caught up" /> : openTasks.slice(0, 6).map((t) => (
              <div key={t.id} className="list-item">
                <i className={`bi ${t.priority === 'high' ? 'bi-exclamation-circle-fill' : 'bi-circle'}`} style={{ color: t.priority === 'high' ? 'var(--red)' : 'var(--sage-400)', marginTop: 3 }} />
                <div style={{ flex: 1 }}>
                  <div className="strong">{t.title}</div>
                  <div className="small muted">Due {fmtDate(t.due_date)}{t.case ? ` · ${byId(caseList, t.case)?.case_number || ''}` : ''}</div>
                </div>
                <Badge value={t.status} />
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head"><h3>Scheduled appointments</h3><Link to="/dashboard/appointments" className="small">View all</Link></div>
          <div className="panel-body">
            {appts.loading ? <Spinner /> : upcomingAppts.length === 0 ? <Empty icon="bi-calendar2" title="No scheduled appointments" /> : upcomingAppts.map((a) => (
              <div key={a.id} className="list-item">
                <i className="bi bi-calendar-event" style={{ color: 'var(--brass)', marginTop: 3 }} />
                <div style={{ flex: 1 }}>
                  <div className="strong">{byId(clients, a.client)?.full_name || `Client #${a.client}`}</div>
                  <div className="small muted">{fmtDateTime(a.start)} · {label(a.appointment_type)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head"><h3>New consultation requests</h3><Link to="/dashboard/consultations" className="small">Manage</Link></div>
          <div className="panel-body">
            {consultations.loading ? <Spinner /> : (consultations.data?.results || []).length === 0 ? <Empty icon="bi-inbox" title="No new requests" /> : consultations.data.results.slice(0, 5).map((c) => (
              <div key={c.id} className="list-item">
                <div className="avatar">{c.name.slice(0, 1).toUpperCase()}</div>
                <div style={{ flex: 1 }}>
                  <div className="strong">{c.name}</div>
                  <div className="small muted">{c.message.slice(0, 80)}{c.message.length > 80 ? '…' : ''}</div>
                </div>
                <span className="small muted">{fmtDate(c.created_at)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
