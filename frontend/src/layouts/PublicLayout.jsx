import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useLang } from '../context/LangContext';
import { useFetch } from '../utils/hooks';

export function LangToggle() {
  const { lang, setLang } = useLang();
  return (
    <div className="lang-toggle" role="group" aria-label="Language">
      <button type="button" className={lang === 'en' ? 'on' : ''} onClick={() => setLang('en')}>EN</button>
      <button type="button" className={lang === 'bn' ? 'on' : ''} onClick={() => setLang('bn')}>বাং</button>
    </div>
  );
}

export default function PublicLayout() {
  const { t } = useLang();
  const { user, isFirm, isClient } = useAuth();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const { data: firm } = useFetch('/api/firm/profile/', { auth: false });
  const { data: areas } = useFetch('/api/practice-areas/', { auth: false });

  useEffect(() => { setOpen(false); window.scrollTo(0, 0); }, [location.pathname]);

  const links = [
    ['/', t('home')], ['/practice-areas', t('practice')], ['/lawyers', t('lawyers')],
    ['/legal-aid', t('legalAid')], ['/knowledge', t('knowledge')], ['/academy', t('academy')], ['/contact', t('contact')],
  ];

  return (
    <>
      <div className="topbar">
        <div className="container">
          <div className="flex">
            {firm?.phone && <a href={`tel:${firm.phone}`}><i className="bi bi-telephone" /> {firm.phone}</a>}
            {firm?.email && <a href={`mailto:${firm.email}`} className="hide-sm"><i className="bi bi-envelope" /> {firm.email}</a>}
            {firm?.working_hours && <span className="hide-sm"><i className="bi bi-clock" /> {firm.working_hours}</span>}
          </div>
          <div className="flex">
            <Link to="/legal-aid/track" className="hide-sm">{t('track')}</Link>
            <LangToggle />
          </div>
        </div>
      </div>
      <header className="navbar">
        <div className="container">
          <Link to="/" className="brand" aria-label="Anadi Law Firm home"><img src="/logo-horizontal.png" alt="Anadi Law Firm" /></Link>
          <ul className={`nav-links${open ? ' open' : ''}`}>
            {links.map(([to, text]) => (
              <li key={to}><NavLink to={to} end={to === '/'}>{text}</NavLink></li>
            ))}
            {!user && <li className="nav-mobile"><NavLink to="/login">{t('login')}</NavLink></li>}
          </ul>
          <div className="nav-cta">
            {user ? (
              <Link to={isFirm ? '/dashboard' : isClient ? '/portal' : '/'} className="btn btn-outline btn-sm">
                <i className="bi bi-grid" /> {isFirm ? t('dashboard') : t('portal')}
              </Link>
            ) : (
              <Link to="/login" className="btn btn-ghost btn-sm"><i className="bi bi-person" /> {t('login')}</Link>
            )}
            <Link to="/consultation" className="btn btn-primary btn-sm">{t('book')}</Link>
            <button type="button" className="burger" onClick={() => setOpen((o) => !o)} aria-label="Menu"><i className={`bi ${open ? 'bi-x' : 'bi-list'}`} /></button>
          </div>
        </div>
      </header>

      <main><Outlet context={{ firm, areas: areas?.results || [] }} /></main>

      <footer className="footer">
        <div className="container">
          <div className="grid">
            <div>
              <Link to="/" className="brand"><img src="/logo-horizontal-light.png" alt="Anadi Law Firm" /></Link>
              <p style={{ maxWidth: 320 }}>{firm?.tagline || 'Counsel rooted in integrity.'}</p>
              <div className="socials">
                {firm?.facebook_url && <a href={firm.facebook_url} target="_blank" rel="noreferrer" aria-label="Facebook"><i className="bi bi-facebook" /></a>}
                {firm?.linkedin_url && <a href={firm.linkedin_url} target="_blank" rel="noreferrer" aria-label="LinkedIn"><i className="bi bi-linkedin" /></a>}
                {firm?.website_url && <a href={firm.website_url} target="_blank" rel="noreferrer" aria-label="Website"><i className="bi bi-globe2" /></a>}
                <a href={firm?.email ? `mailto:${firm.email}` : '/contact'} aria-label="Email"><i className="bi bi-envelope" /></a>
              </div>
            </div>
            <div>
              <h4>{t('practice')}</h4>
              <ul>{(areas?.results || []).slice(0, 6).map((a) => <li key={a.id}><Link to={`/practice-areas/${a.slug}`}>{a.name}</Link></li>)}</ul>
            </div>
            <div>
              <h4>{t('quickLinks')}</h4>
              <ul>
                <li><Link to="/consultation">{t('book')}</Link></li>
                <li><Link to="/legal-aid">{t('legalAid')}</Link></li>
                <li><Link to="/knowledge/guided">{t('guided')}</Link></li>
                <li><Link to="/academy">{t('academy')}</Link></li>
                <li><Link to="/login">{t('login')}</Link></li>
              </ul>
            </div>
            <div>
              <h4>{t('reachUs')}</h4>
              <ul>
                {firm?.address && <li><i className="bi bi-geo-alt" /> {firm.address}</li>}
                {firm?.phone && <li><i className="bi bi-telephone" /> {firm.phone}</li>}
                {firm?.email && <li><i className="bi bi-envelope" /> {firm.email}</li>}
                {firm?.working_hours && <li><i className="bi bi-clock" /> {firm.working_hours}</li>}
              </ul>
            </div>
          </div>
          <div className="footer-bottom">
            <span>© {new Date().getFullYear()} {firm?.name || 'Anadi Law Firm'}. {t('allRights')}</span>
            <span>{t('disclaimer')}</span>
          </div>
        </div>
      </footer>
    </>
  );
}
