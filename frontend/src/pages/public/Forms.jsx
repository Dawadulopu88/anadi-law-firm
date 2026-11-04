import { useEffect, useState } from 'react';
import { Link, useNavigate, useOutletContext, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../../api/client';
import { ErrorBox, Field, PageHero, Spinner } from '../../components/UI';
import { useLang } from '../../context/LangContext';
import { label, todayISO } from '../../utils/format';

function usePublicForm(initial) {
  const [values, setValues] = useState(initial);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (name) => (v) => setValues((s) => ({ ...s, [name]: v }));
  const run = async (fn) => {
    setBusy(true); setErrors({}); setError(null);
    try { return await fn(); } catch (err) { setErrors(err.fields || {}); setError(err); return null; } finally { setBusy(false); }
  };
  return { values, set, errors, error, busy, run, setValues };
}

function SuccessCard({ icon = 'bi-check2-circle', title, children }) {
  return (
    <div className="card center reveal" style={{ padding: 44 }}>
      <div className="icon-badge" style={{ margin: '0 auto 18px', width: 70, height: 70, fontSize: '2rem' }}><i className={`bi ${icon}`} /></div>
      <h2>{title}</h2>
      {children}
    </div>
  );
}

export function Consultation() {
  const { t, lang } = useLang();
  const { areas, firm } = useOutletContext();
  const [params] = useSearchParams();
  const f = usePublicForm({ name: '', phone: '', email: '', practice_area: params.get('area') || '', message: '', preferred_date: '', preferred_language: lang, website: '' });
  const [done, setDone] = useState(null);

  const submit = (e) => {
    e.preventDefault();
    f.run(async () => {
      const body = { ...f.values, preferred_date: f.values.preferred_date || null, email: f.values.email || '' };
      setDone(await api.post('/api/consultations/', body, { auth: false }));
    });
  };

  return (
    <>
      <PageHero eyebrow={t('book')} title={t('ctaTitle')} text={t('ctaText')} crumbs={[{ label: t('book') }]} />
      <section className="section">
        <div className="container split split-wide">
          {done ? (
            <SuccessCard title={lang === 'bn' ? 'অনুরোধ পাওয়া গেছে' : 'Request received'}>
              <p className="lead">{lang === 'bn' ? 'ধন্যবাদ। আমাদের টিম শীঘ্রই আপনার সাথে যোগাযোগ করবে।' : 'Thank you. Our team will contact you shortly to arrange your consultation.'}</p>
              <p className="muted small">Reference #{done.id}</p>
              <Link to="/" className="btn btn-primary mt-2">{t('home')}</Link>
            </SuccessCard>
          ) : (
            <form className="card form-grid" onSubmit={submit} noValidate>
              <div className="full"><ErrorBox error={f.error} /></div>
              <Field label={t('name')} name="name" required value={f.values.name} onChange={f.set('name')} error={f.errors.name} />
              <Field label={t('phone')} name="phone" type="tel" required value={f.values.phone} onChange={f.set('phone')} error={f.errors.phone} />
              <Field label={t('email')} name="email" type="email" value={f.values.email} onChange={f.set('email')} error={f.errors.email} />
              <Field label={t('area')} name="practice_area" type="select" required value={f.values.practice_area} onChange={f.set('practice_area')} error={f.errors.practice_area}
                options={areas.map((a) => ({ value: a.id, label: a.name }))} />
              <Field label={t('preferredDate')} name="preferred_date" type="date" min={todayISO()} value={f.values.preferred_date} onChange={f.set('preferred_date')} error={f.errors.preferred_date} />
              <Field label={t('preferredLanguage')} name="preferred_language" type="select" value={f.values.preferred_language} onChange={f.set('preferred_language')}
                options={[{ value: 'en', label: 'English' }, { value: 'bn', label: 'বাংলা' }]} />
              <Field full label={t('message')} name="message" type="textarea" required value={f.values.message} onChange={f.set('message')} error={f.errors.message}
                hint={lang === 'bn' ? 'সংক্ষেপে আপনার বিষয়টি লিখুন (সর্বোচ্চ ৫০০০ অক্ষর)।' : 'Briefly describe your matter (max 5000 characters).'} />
              <input className="hp" tabIndex={-1} autoComplete="off" name="website" value={f.values.website} onChange={(e) => f.set('website')(e.target.value)} aria-hidden="true" />
              <div className="full flex between flex-wrap">
                <span className="small muted">{t('disclaimer')}</span>
                <button className="btn btn-primary" disabled={f.busy}>{f.busy ? t('sending') : <><i className="bi bi-send" /> {t('submit')}</>}</button>
              </div>
            </form>
          )}
          <aside className="stack">
            <div className="card">
              <h3>{lang === 'bn' ? 'কী আশা করবেন' : 'What to expect'}</h3>
              <ul className="info-list">
                <li><i className="bi bi-1-circle" /><div>{lang === 'bn' ? 'আপনার অনুরোধ পর্যালোচনা করা হবে' : 'We review your request'}</div></li>
                <li><i className="bi bi-2-circle" /><div>{lang === 'bn' ? 'একজন টিম সদস্য যোগাযোগ করবেন' : 'A team member contacts you'}</div></li>
                <li><i className="bi bi-3-circle" /><div>{lang === 'bn' ? 'উপযুক্ত আইনজীবীর সাথে পরামর্শ' : 'Consult the right advocate'}</div></li>
              </ul>
            </div>
            {firm && (
              <div className="card section-cream" style={{ border: 0 }}>
                <h4>{t('reachUs')}</h4>
                {firm.phone && <p className="mb-0"><i className="bi bi-telephone" /> {firm.phone}</p>}
                {firm.email && <p className="mb-0"><i className="bi bi-envelope" /> {firm.email}</p>}
                {firm.working_hours && <p className="mb-0"><i className="bi bi-clock" /> {firm.working_hours}</p>}
              </div>
            )}
          </aside>
        </div>
      </section>
    </>
  );
}

const INCOME = ['Below ৳10,000 / month', '৳10,000 – ৳20,000 / month', '৳20,000 – ৳40,000 / month', 'Above ৳40,000 / month', 'Prefer not to say'];

export function LegalAidApply() {
  const { t, lang } = useLang();
  const { areas } = useOutletContext();
  const f = usePublicForm({ applicant_name: '', phone: '', email: '', practice_area: '', description: '', income_range: '', household_size: '', has_ongoing_case: false, website: '' });
  const [done, setDone] = useState(null);

  const submit = (e) => {
    e.preventDefault();
    f.run(async () => {
      const { household_size, has_ongoing_case, ...rest } = f.values;
      const eligibility_answers = { has_ongoing_case };
      if (household_size) eligibility_answers.household_size = Number(household_size);
      setDone(await api.post('/api/legal-aid/apply/', { ...rest, eligibility_answers }, { auth: false }));
    });
  };

  return (
    <>
      <PageHero eyebrow={t('legalAid')} title={t('legalAidTitle')} text={t('legalAidText')} crumbs={[{ label: t('legalAid') }]} />
      <section className="section">
        <div className="container split split-wide">
          {done ? (
            <SuccessCard icon="bi-shield-lock" title={lang === 'bn' ? 'আবেদন জমা হয়েছে' : 'Application submitted'}>
              <p>{lang === 'bn' ? 'এই গোপন ট্র্যাকিং কোডটি সংরক্ষণ করুন। এটি আর দেখানো হবে না।' : 'Save this private tracking code now — it will not be shown again.'}</p>
              <div className="code-box">{done.tracking_code}</div>
              <div className="flex mt-2" style={{ justifyContent: 'center' }}>
                <button type="button" className="btn btn-outline btn-sm" onClick={() => navigator.clipboard?.writeText(done.tracking_code)}><i className="bi bi-clipboard" /> Copy</button>
                <Link to={`/legal-aid/track/${encodeURIComponent(done.tracking_code)}`} className="btn btn-primary btn-sm">{t('track')}</Link>
              </div>
            </SuccessCard>
          ) : (
            <form className="card form-grid" onSubmit={submit} noValidate>
              <div className="full"><ErrorBox error={f.error} /></div>
              <Field label={t('name')} name="applicant_name" required value={f.values.applicant_name} onChange={f.set('applicant_name')} error={f.errors.applicant_name} />
              <Field label={t('phone')} name="phone" required value={f.values.phone} onChange={f.set('phone')} error={f.errors.phone} />
              <Field label={t('email')} name="email" type="email" value={f.values.email} onChange={f.set('email')} error={f.errors.email} />
              <Field label={t('area')} name="practice_area" type="select" required value={f.values.practice_area} onChange={f.set('practice_area')} error={f.errors.practice_area}
                options={areas.map((a) => ({ value: a.id, label: a.name }))} />
              <Field label={lang === 'bn' ? 'মাসিক আয়ের পরিসীমা' : 'Monthly income range'} name="income_range" type="select" value={f.values.income_range} onChange={f.set('income_range')}
                options={INCOME.map((x) => ({ value: x, label: x }))} />
              <Field label={lang === 'bn' ? 'পরিবারের সদস্য সংখ্যা' : 'Household size'} name="household_size" type="number" min="1" max="30" value={f.values.household_size} onChange={f.set('household_size')} />
              <Field full type="checkbox" name="has_ongoing_case" label={lang === 'bn' ? 'আমার একটি চলমান মামলা আছে' : 'I already have an ongoing court case'} value={f.values.has_ongoing_case} onChange={f.set('has_ongoing_case')} />
              <Field full label={lang === 'bn' ? 'আপনার সমস্যার বিবরণ' : 'Describe your situation'} name="description" type="textarea" required value={f.values.description} onChange={f.set('description')} error={f.errors.description || f.errors.eligibility_answers} />
              <input className="hp" tabIndex={-1} autoComplete="off" value={f.values.website} onChange={(e) => f.set('website')(e.target.value)} aria-hidden="true" />
              <div className="full flex between flex-wrap">
                <span className="small muted">{lang === 'bn' ? 'আবেদন জমা দেওয়া মানে যোগ্যতার নিশ্চয়তা নয়।' : 'Submitting does not guarantee eligibility.'}</span>
                <button className="btn btn-primary" disabled={f.busy}>{f.busy ? t('sending') : t('apply')}</button>
              </div>
            </form>
          )}
          <aside className="stack">
            <div className="card">
              <div className="icon-badge brass"><i className="bi bi-search-heart" /></div>
              <h3>{t('track')}</h3>
              <p className="muted">{lang === 'bn' ? 'আগে আবেদন করেছেন? কোড দিয়ে অবস্থা দেখুন।' : 'Already applied? Check the status with your code.'}</p>
              <Link to="/legal-aid/track" className="btn btn-outline btn-block">{t('track')}</Link>
            </div>
            <div className="card">
              <div className="icon-badge"><i className="bi bi-signpost-split" /></div>
              <h3>{t('guided')}</h3>
              <p className="muted">{lang === 'bn' ? 'আপনার যোগ্যতা সম্পর্কে একটি প্রাথমিক ধারণা নিন।' : 'Get an indicative idea of your eligibility first.'}</p>
              <Link to="/knowledge/guided" className="btn btn-ghost btn-block">{t('guided')}</Link>
            </div>
          </aside>
        </div>
      </section>
    </>
  );
}

const AID_STEPS = ['submitted', 'under_review', 'matched'];

export function LegalAidTrack() {
  const { t, lang } = useLang();
  const { code: initial } = useParams();
  const navigate = useNavigate();
  const [code, setCode] = useState(initial || '');
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const check = async (e, override) => {
    e?.preventDefault();
    const value = (override ?? code).trim();
    if (!value) return;
    setBusy(true); setError(null); setStatus(null);
    try {
      const data = await api.public(`/api/legal-aid/track/${encodeURIComponent(value)}/`);
      setStatus(data.status);
      if (initial) navigate('/legal-aid/track', { replace: true });
    } catch (err) {
      setError(err.status === 404 ? new Error(lang === 'bn' ? 'এই কোডে কোনো আবেদন পাওয়া যায়নি।' : 'No application found for this code.') : err);
    } finally { setBusy(false); }
  };

  // Arriving from the submission screen: check once, then drop the code from the URL.
  useEffect(() => { if (initial) check(null, initial); }, [initial]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <PageHero eyebrow={t('legalAid')} title={t('track')} text={lang === 'bn' ? 'জমা দেওয়ার সময় পাওয়া গোপন কোডটি লিখুন।' : 'Enter the private code you received when you applied.'} crumbs={[{ label: t('legalAid'), to: '/legal-aid' }, { label: t('track') }]} />
      <section className="section">
        <div className="container" style={{ maxWidth: 720 }}>
          <form className="searchbar" onSubmit={check}>
            <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="Tracking code" aria-label="Tracking code" />
            <button className="btn btn-primary" disabled={busy}>{busy ? <Spinner small /> : t('track')}</button>
          </form>
          <div className="mt-3"><ErrorBox error={error} /></div>
          {status && (
            <div className="card mt-3 reveal">
              <div className="flex between"><h3 className="mb-0">Application status</h3><span className={`badge tone-${status === 'declined' ? 'red' : status === 'matched' ? 'green' : 'amber'}`}>{label(status)}</span></div>
              {status !== 'declined' ? (
                <div className="flex mt-3" style={{ gap: 0 }}>
                  {AID_STEPS.map((s, i) => {
                    const reached = AID_STEPS.indexOf(status) >= i;
                    return (
                      <div key={s} style={{ flex: 1, textAlign: 'center' }}>
                        <div style={{ height: 6, background: reached ? 'var(--sage-500)' : 'var(--sage-100)', borderRadius: 4, margin: '0 4px 10px' }} />
                        <span className={`small ${reached ? '' : 'muted'}`} style={{ fontWeight: 700 }}>{label(s)}</span>
                      </div>
                    );
                  })}
                </div>
              ) : <p className="muted mt-2">{lang === 'bn' ? 'দুঃখিত, এই আবেদনটি গৃহীত হয়নি। আরও তথ্যের জন্য যোগাযোগ করুন।' : 'Unfortunately this application was not accepted. Please contact the firm for more information.'}</p>}
            </div>
          )}
        </div>
      </section>
    </>
  );
}
