import { useState } from 'react';
import { api } from '../api/client';
import { Badge, ErrorBox, Field, Spinner } from '../components/UI';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { initials } from '../utils/format';

export default function Account() {
  const { user } = useAuth();
  const toast = useToast();
  const [v, setV] = useState({ current_password: '', new_password: '', confirm: '' });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (val) => setV((s) => ({ ...s, [k]: val }));
  const name = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username;

  const submit = async (e) => {
    e.preventDefault();
    if (v.new_password !== v.confirm) { setErrors({ confirm: 'Passwords do not match.' }); return; }
    setBusy(true); setErrors({}); setError(null);
    try {
      await api.post('/api/auth/change-password/', { current_password: v.current_password, new_password: v.new_password });
      toast.success('Password changed');
      setV({ current_password: '', new_password: '', confirm: '' });
    } catch (err) { setErrors(err.fields); setError(err); } finally { setBusy(false); }
  };

  return (
    <div className="grid grid-2" style={{ alignItems: 'start' }}>
      <div className="panel panel-body">
        <div className="flex mb-2">
          <div className="avatar" style={{ width: 64, height: 64, fontSize: '1.3rem' }}>{initials(name)}</div>
          <div><h3 className="mb-0">{name}</h3><Badge value={user.role} /></div>
        </div>
        <ul className="info-list">
          <li><i className="bi bi-person" /><div><strong>Username</strong>{user.username}</div></li>
          <li><i className="bi bi-envelope" /><div><strong>Email</strong>{user.email || '—'}</div></li>
          <li><i className="bi bi-telephone" /><div><strong>Phone</strong>{user.phone || '—'}</div></li>
        </ul>
        <p className="small muted mt-2 mb-0">To update your profile details, contact the firm administrator.</p>
      </div>
      <form className="panel panel-body stack" onSubmit={submit}>
        <h3 className="mb-0">Change password</h3>
        <ErrorBox error={error} />
        <Field label="Current password" name="current_password" type="password" required value={v.current_password} onChange={set('current_password')} error={errors.current_password} />
        <Field label="New password" name="new_password" type="password" required value={v.new_password} onChange={set('new_password')} error={errors.new_password} hint="At least 8 characters; not common or numbers only." />
        <Field label="Confirm new password" name="confirm" type="password" required value={v.confirm} onChange={set('confirm')} error={errors.confirm} />
        <button className="btn btn-primary" disabled={busy}>{busy ? <Spinner small /> : 'Update password'}</button>
      </form>
    </div>
  );
}
