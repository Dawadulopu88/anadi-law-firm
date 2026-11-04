import { useState } from 'react';
import { api } from '../../api/client';
import { Empty, ErrorBox, Field, Modal, PageHero, Spinner } from '../../components/UI';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../context/ToastContext';
import { fmtDateTime, label } from '../../utils/format';
import { useFetch } from '../../utils/hooks';

function RegisterModal({ session, onClose, onDone }) {
  const { t } = useLang();
  const toast = useToast();
  const [v, setV] = useState({ name: '', email: '', phone: '', website: '' });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (val) => setV((s) => ({ ...s, [k]: val }));
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErrors({}); setError(null);
    try {
      await api.post('/api/session-registrations/', { ...v, session: session.id });
      toast.success('You are registered! See you there.');
      onDone();
    } catch (err) { setErrors(err.fields); setError(err); } finally { setBusy(false); }
  };
  return (
    <Modal title={`${t('register')}: ${session.title}`} onClose={onClose} footer={(
      <><button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button form="reg-form" className="btn btn-primary" disabled={busy}>{busy ? <Spinner small /> : t('register')}</button></>
    )}>
      <form id="reg-form" className="form-grid" onSubmit={submit}>
        <div className="full"><ErrorBox error={error} /></div>
        <Field label={t('name')} name="name" required value={v.name} onChange={set('name')} error={errors.name} />
        <Field label={t('email')} name="email" type="email" required value={v.email} onChange={set('email')} error={errors.email} />
        <Field label={t('phone')} name="phone" value={v.phone} onChange={set('phone')} error={errors.phone} />
        <input className="hp" tabIndex={-1} autoComplete="off" value={v.website} onChange={(e) => set('website')(e.target.value)} aria-hidden="true" />
      </form>
    </Modal>
  );
}

export default function Academy() {
  const { t, lang } = useLang();
  const [pathway, setPathway] = useState('');
  const pathways = useFetch('/api/pathways/', { auth: false });
  const courses = useFetch(`/api/courses/${pathway ? `?pathway=${pathway}` : ''}`, { auth: false });
  const sessions = useFetch('/api/live-sessions/', { auth: false });
  const [reg, setReg] = useState(null);

  return (
    <>
      <PageHero eyebrow={t('academy')} title={lang === 'bn' ? 'অনাদি একাডেমি' : 'Anadi Academy'} text={lang === 'bn' ? 'আইনি সচেতনতার কোর্স ও লাইভ সেশন।' : 'Legal-awareness courses and live sessions for everyone.'} crumbs={[{ label: t('academy') }]} />
      <section className="section">
        <div className="container">
          <div className="section-head">
            <div><div className="eyebrow">{t('sessions')}</div><h2 className="mb-0">{lang === 'bn' ? 'আসন্ন লাইভ সেশন' : 'Upcoming live sessions'}</h2></div>
          </div>
          <ErrorBox error={sessions.error} />
          {sessions.loading ? <Spinner /> : (sessions.data?.results || []).length === 0 ? <Empty icon="bi-camera-video" title="No upcoming sessions" /> : (
            <div className="grid grid-3">
              {sessions.data.results.map((s) => {
                const pct = s.capacity ? Math.round(((s.capacity - s.seats_remaining) / s.capacity) * 100) : 0;
                const d = new Date(s.start);
                return (
                  <div key={s.id} className="card card-hover">
                    <div className="flex mb-2">
                      <div className="date-tile"><b>{d.getDate()}</b><small>{d.toLocaleString('en', { month: 'short' })}</small></div>
                      <div><h4 className="mb-0">{s.title}</h4><span className="small muted">{fmtDateTime(s.start)}</span></div>
                    </div>
                    {s.venue && <p className="small mb-0"><i className="bi bi-geo-alt" /> {s.venue}</p>}
                    {s.meeting_link && <p className="small mb-0"><i className="bi bi-camera-video" /> Online session</p>}
                    <div className="mt-2"><div className="progress"><div style={{ width: `${pct}%` }} /></div>
                      <span className="small muted">{s.seats_remaining} / {s.capacity} {t('seatsLeft')}</span></div>
                    <button type="button" className="btn btn-primary btn-block mt-2" disabled={s.seats_remaining < 1} onClick={() => setReg(s)}>
                      {s.seats_remaining < 1 ? 'Full' : t('register')}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </section>
      <section className="section section-cream">
        <div className="container">
          <div className="section-head">
            <div><div className="eyebrow">{t('courses')}</div><h2 className="mb-0">{lang === 'bn' ? 'কোর্সসমূহ' : 'Course catalogue'}</h2></div>
            <div className="tabs mb-0">
              <button type="button" className={!pathway ? 'on' : ''} onClick={() => setPathway('')}>All</button>
              {(pathways.data?.results || []).map((p) => <button key={p.id} type="button" className={String(pathway) === String(p.id) ? 'on' : ''} onClick={() => setPathway(p.id)}>{p.title}</button>)}
            </div>
          </div>
          {courses.loading ? <Spinner /> : (courses.data?.results || []).length === 0 ? <Empty icon="bi-mortarboard" title="No courses yet" /> : (
            <div className="grid grid-3">
              {courses.data.results.map((c) => (
                <div key={c.id} className="card card-hover">
                  <div className="flex between mb-2"><span className="chip">{label(c.level)}</span>{c.is_sample && <span className="badge tone-amber">Sample</span>}</div>
                  <h3>{c.title}</h3>
                  <p className="muted small">{c.summary}</p>
                  <div className="flex between small"><span><i className="bi bi-person-video3" /> {c.instructor}</span><span><i className="bi bi-clock" /> {c.duration}</span></div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
      {reg && <RegisterModal session={reg} onClose={() => setReg(null)} onDone={() => { setReg(null); sessions.reload(); }} />}
    </>
  );
}
