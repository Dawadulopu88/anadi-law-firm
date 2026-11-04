import { useEffect, useState } from 'react';
import { Link, NavLink, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Spinner } from '../components/UI';
import { useAuth } from '../context/AuthContext';
import { useLang } from '../context/LangContext';
import { initials, label } from '../utils/format';
import { LangToggle } from './PublicLayout';

const FIRM_NAV = [
  { group: 'Overview' },
  { to: '/dashboard', icon: 'bi-grid-1x2', text: 'Dashboard', end: true },
  { group: 'Intake' },
  { to: '/dashboard/consultations', icon: 'bi-chat-square-text', text: 'Consultations' },
  { to: '/dashboard/legal-aid', icon: 'bi-heart-pulse', text: 'Legal aid' },
  { to: '/dashboard/clients', icon: 'bi-people', text: 'Clients' },
  { group: 'Casework' },
  { to: '/dashboard/cases', icon: 'bi-briefcase', text: 'Cases' },
  { to: '/dashboard/hearings', icon: 'bi-bank', text: 'Hearings' },
  { to: '/dashboard/appointments', icon: 'bi-calendar2-week', text: 'Appointments' },
  { to: '/dashboard/tasks', icon: 'bi-check2-square', text: 'Tasks' },
  { to: '/dashboard/documents', icon: 'bi-folder2-open', text: 'Documents' },
  { group: 'Finance' },
  { to: '/dashboard/invoices', icon: 'bi-receipt', text: 'Invoices' },
  { to: '/dashboard/payments', icon: 'bi-cash-coin', text: 'Payments' },
  { group: 'Administration', roles: ['admin'] },
  { to: '/dashboard/users', icon: 'bi-person-gear', text: 'User accounts', roles: ['admin'] },
];

const PORTAL_NAV = [
  { group: 'My portal' },
  { to: '/portal', icon: 'bi-grid-1x2', text: 'Overview', end: true },
  { to: '/portal/cases', icon: 'bi-briefcase', text: 'My cases' },
  { to: '/portal/hearings', icon: 'bi-bank', text: 'Hearings' },
  { to: '/portal/appointments', icon: 'bi-calendar2-week', text: 'Appointments' },
  { to: '/portal/documents', icon: 'bi-folder2-open', text: 'Documents' },
  { to: '/portal/invoices', icon: 'bi-receipt', text: 'Invoices' },
];

function titleFor(nav, pathname) {
  const match = nav.filter((n) => n.to && (pathname === n.to || pathname.startsWith(`${n.to}/`)))
    .sort((a, b) => b.to.length - a.to.length)[0];
  return match?.text || 'Dashboard';
}

export default function AppLayout({ area }) {
  const { user, ready, isFirm, isClient, logout } = useAuth();
  const { t } = useLang();
  const location = useLocation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [location.pathname]);

  if (!ready) return <Spinner />;
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  if (area === 'firm' && !isFirm) return <Navigate to={isClient ? '/portal' : '/'} replace />;
  if (area === 'portal' && !isClient) return <Navigate to={isFirm ? '/dashboard' : '/'} replace />;

  const nav = ((area === 'firm' || (area === 'any' && isFirm)) ? FIRM_NAV : PORTAL_NAV).filter((n) => !n.roles || n.roles.includes(user.role));
  const name = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username;

  return (
    <div className="app">
      <aside className={`sidebar${open ? ' open' : ''}`}>
        <Link to="/" className="brand"><img src="/logo-horizontal-light.png" alt="Anadi Law Firm" /></Link>
        <nav>
          {nav.map((n) => (n.group
            ? <div key={n.group} className="side-group">{n.group}</div>
            : <NavLink key={n.to} to={n.to} end={n.end} className="side-link"><i className={`bi ${n.icon}`} /> {n.text}</NavLink>))}
        </nav>
        <div className="side-foot">
          <Link to="/account" className="side-link"><i className="bi bi-shield-lock" /> Account & password</Link>
          <Link to="/" className="side-link"><i className="bi bi-globe2" /> Public website</Link>
          <button type="button" className="side-link" style={{ background: 'none', border: 0, width: '100%', cursor: 'pointer', font: 'inherit' }}
            onClick={() => { logout(); navigate('/login'); }}>
            <i className="bi bi-box-arrow-left" /> {t('logout')}
          </button>
        </div>
      </aside>
      <div className="main">
        <header className="appbar">
          <div className="flex">
            <button type="button" className="icon-btn mobile-only" onClick={() => setOpen((o) => !o)} aria-label="Menu"><i className="bi bi-list" /></button>
            <h1>{location.pathname === '/account' ? 'My account' : titleFor(nav, location.pathname)}</h1>
          </div>
          <div className="flex">
            <LangToggleLight />
            <div className="user-chip">
              <div className="avatar">{initials(name)}</div>
              <div style={{ lineHeight: 1.2 }}>
                <div style={{ fontWeight: 700, fontSize: '.86rem' }}>{name}</div>
                <div className="small muted">{label(user.role)}</div>
              </div>
            </div>
          </div>
        </header>
        <div className="content"><Outlet /></div>
      </div>
      {open && <div className="modal-back" style={{ zIndex: 55, background: 'rgba(0,0,0,.3)' }} onClick={() => setOpen(false)} />}
    </div>
  );
}

function LangToggleLight() {
  return <div style={{ background: 'var(--forest-800)', borderRadius: 999, padding: 2 }}><LangToggle /></div>;
}
