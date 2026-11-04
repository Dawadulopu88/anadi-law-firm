import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { STATUS_TONE, label } from '../utils/format';

export const Spinner = ({ small }) => <div className={`spinner${small ? ' sm' : ''}`} aria-label="Loading" />;

export function Empty({ icon = 'bi-inbox', title = 'Nothing here yet', children }) {
  return (
    <div className="empty">
      <i className={`bi ${icon}`} />
      <div style={{ fontWeight: 700, color: 'var(--ink-soft)' }}>{title}</div>
      {children && <div className="small" style={{ marginTop: 4 }}>{children}</div>}
    </div>
  );
}

export function ErrorBox({ error, onRetry }) {
  if (!error) return null;
  return (
    <div className="alert alert-error">
      <i className="bi bi-exclamation-triangle" />
      <div style={{ flex: 1 }}>{error.message || String(error)}</div>
      {onRetry && <button type="button" className="btn btn-xs btn-danger" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function Badge({ value, tone, children }) {
  const t = tone || STATUS_TONE[value] || 'grey';
  return <span className={`badge tone-${t}`}>{children || label(value)}</span>;
}

export function Modal({ title, onClose, children, footer, size }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose?.();
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => { document.removeEventListener('keydown', onKey); document.body.style.overflow = ''; };
  }, [onClose]);
  return (
    <div className="modal-back" onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}>
      <div className={`modal${size === 'sm' ? ' modal-sm' : ''}`} role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-head">
          <h3>{title}</h3>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close"><i className="bi bi-x-lg" /></button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  );
}

export function Confirm({ title = 'Are you sure?', message, confirmText = 'Confirm', danger, busy, onConfirm, onClose }) {
  return (
    <Modal title={title} onClose={onClose} size="sm" footer={(
      <>
        <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button type="button" className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`} onClick={onConfirm} disabled={busy}>
          {busy ? <Spinner small /> : confirmText}
        </button>
      </>
    )}>
      <p className="mb-0">{message}</p>
    </Modal>
  );
}

export function Field({ label: text, name, type = 'text', value, onChange, options, required, error, hint, full, placeholder, disabled, min, max, step, rows }) {
  const id = `f-${name}`;
  const common = { id, name, required, disabled, placeholder };
  let control;
  if (type === 'select') {
    control = (
      <select {...common} value={value ?? ''} onChange={(e) => onChange(e.target.value)}>
        <option value="">{placeholder || '— Select —'}</option>
        {(options || []).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    );
  } else if (type === 'textarea') {
    control = <textarea {...common} rows={rows} value={value ?? ''} onChange={(e) => onChange(e.target.value)} />;
  } else if (type === 'checkbox') {
    return (
      <label className={`check${full ? ' full' : ''}`} htmlFor={id}>
        <input id={id} type="checkbox" checked={!!value} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
        {text}
      </label>
    );
  } else if (type === 'file') {
    control = <input {...common} type="file" onChange={(e) => onChange(e.target.files?.[0] || null)} />;
  } else {
    control = <input {...common} type={type} min={min} max={max} step={step} value={value ?? ''} onChange={(e) => onChange(e.target.value)} />;
  }
  return (
    <div className={`field${error ? ' has-err' : ''}${full ? ' full' : ''}`}>
      {text && <label htmlFor={id}>{text}{required && <span className="req"> *</span>}</label>}
      {control}
      {hint && !error && <span className="hint">{hint}</span>}
      {error && <span className="err">{error}</span>}
    </div>
  );
}

export function Pagination({ data, page, setPage }) {
  if (!data || (!data.next && !data.previous)) return null;
  const total = Math.max(1, Math.ceil((data.count || 0) / 20));
  return (
    <div className="pager">
      <span>Page {page} of {total} · {data.count} records</span>
      <div className="flex">
        <button type="button" className="btn btn-xs btn-outline" disabled={!data.previous} onClick={() => setPage(page - 1)}><i className="bi bi-chevron-left" /> Prev</button>
        <button type="button" className="btn btn-xs btn-outline" disabled={!data.next} onClick={() => setPage(page + 1)}>Next <i className="bi bi-chevron-right" /></button>
      </div>
    </div>
  );
}

export function PageHero({ eyebrow, title, text, crumbs }) {
  return (
    <section className="page-hero">
      <div className="container reveal">
        {crumbs && (
          <div className="crumbs">
            <Link to="/">Home</Link>
            {crumbs.map((c) => <span key={c.label}> / {c.to ? <Link to={c.to}>{c.label}</Link> : c.label}</span>)}
          </div>
        )}
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {text && <p>{text}</p>}
      </div>
    </section>
  );
}

export function AreaIcon({ icon, fallback = 'bi-bank2' }) {
  const cls = icon && /^bi-[a-z0-9-]+$/.test(icon) ? icon : fallback;
  return <i className={`bi ${cls}`} />;
}
