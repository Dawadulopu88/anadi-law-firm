import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ErrorBox, Field, Spinner } from '../../components/UI';
import { useAuth } from '../../context/AuthContext';
import { useLang } from '../../context/LangContext';

export default function Login() {
  const { login, user, isFirm } = useAuth();
  const { t, lang } = useLang();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={isFirm ? '/dashboard' : user.role === 'client' ? '/portal' : '/'} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const me = await login(username.trim(), password);
      const from = location.state?.from;
      const home = ['admin', 'staff', 'lawyer'].includes(me.role) ? '/dashboard' : '/portal';
      navigate(from && from.startsWith(home) ? from : home, { replace: true });
    } catch (err) {
      setError(err.status === 401 ? new Error(lang === 'bn' ? 'ইউজারনেম বা পাসওয়ার্ড সঠিক নয়।' : 'Incorrect username or password.') : err);
    } finally { setBusy(false); }
  };

  return (
    <div className="auth-wrap">
      <div className="auth-art">
        <Link to="/"><img src="/logo-horizontal-light.png" alt="Anadi Law Firm" /></Link>
        <blockquote>“{lang === 'bn' ? 'ন্যায়ের পথে, প্রতিটি পদক্ষেপে আপনার পাশে।' : 'Beside you at every step on the path to justice.'}”</blockquote>
        <div className="small" style={{ color: 'var(--sage-300)' }}>Secure portal for clients, lawyers and firm staff.</div>
      </div>
      <div className="auth-form">
        <form className="card" onSubmit={submit}>
          <img src="/mark.png" alt="" style={{ height: 54, marginBottom: 14 }} />
          <h2 style={{ marginBottom: 4 }}>{lang === 'bn' ? 'স্বাগতম' : 'Welcome back'}</h2>
          <p className="muted">{lang === 'bn' ? 'আপনার অ্যাকাউন্টে লগইন করুন' : 'Sign in to your account'}</p>
          <div className="stack">
            <ErrorBox error={error} />
            <Field label="Username" name="username" required value={username} onChange={setUsername} />
            <Field label="Password" name="password" type="password" required value={password} onChange={setPassword} />
            <button className="btn btn-primary btn-block" disabled={busy || !username || !password}>{busy ? <Spinner small /> : t('login')}</button>
          </div>
          <p className="small muted mt-3 mb-0">
            {lang === 'bn' ? 'অ্যাকাউন্ট নেই? ক্লায়েন্ট লগইন ফার্ম কর্তৃক প্রদান করা হয়।' : 'No account? Client portal logins are issued by the firm.'}{' '}
            <Link to="/consultation">{t('book')}</Link>
          </p>
          <p className="small mt-2 mb-0"><Link to="/"><i className="bi bi-arrow-left" /> {t('home')}</Link></p>
        </form>
      </div>
    </div>
  );
}
