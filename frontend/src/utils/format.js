export const fmtDate = (v) => {
  if (!v) return '—';
  const d = new Date(v.length === 10 ? `${v}T00:00:00` : v);
  return Number.isNaN(d.getTime()) ? v : d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
};

export const fmtDateTime = (v) => {
  if (!v) return '—';
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
};

export const fmtTime = (v) => (v ? new Date(v).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : '');

export const money = (v, currency = 'BDT') => {
  const n = Number(v || 0);
  return `৳ ${n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${currency && currency !== 'BDT' ? ` ${currency}` : ''}`;
};

export const label = (v) => (v == null || v === '' ? '—' : String(v).replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()));

// ISO datetime -> value for <input type="datetime-local">
export const toLocalInput = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

// datetime-local value -> ISO string with timezone
export const fromLocalInput = (v) => (v ? new Date(v).toISOString() : null);

export const todayISO = () => {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

export const initials = (name = '') => name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase() || 'A';

export const STATUS_TONE = {
  open: 'green', in_progress: 'blue', on_hold: 'amber', closed: 'grey', archived: 'grey',
  scheduled: 'blue', completed: 'green', cancelled: 'grey',
  new: 'amber', contacted: 'blue', converted: 'green',
  pending: 'amber', paid: 'green', partial: 'amber', unpaid: 'red',
  submitted: 'amber', under_review: 'blue', matched: 'green', declined: 'red',
  active: 'green', inactive: 'grey', high: 'red', normal: 'blue', low: 'grey',
  lead: 'green', support: 'blue', admin: 'brass', lawyer: 'green', staff: 'blue', client: 'grey',
};
