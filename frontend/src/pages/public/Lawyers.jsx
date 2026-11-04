import { Link, useParams } from 'react-router-dom';
import { Empty, ErrorBox, PageHero, Spinner } from '../../components/UI';
import { useLang } from '../../context/LangContext';
import { initials } from '../../utils/format';
import { useFetch } from '../../utils/hooks';

export function LawyerCard({ lawyer }) {
  const { t } = useLang();
  return (
    <Link to={`/lawyers/${lawyer.id}`} className="card card-hover lawyer-card" style={{ color: 'inherit' }}>
      <div className="lawyer-photo">
        {lawyer.photo ? <img src={lawyer.photo} alt={lawyer.full_name} /> : <div className="monogram">{initials(lawyer.full_name)}</div>}
      </div>
      <div className="lawyer-body">
        <h3>{lawyer.full_name}</h3>
        <div className="title">{lawyer.title}</div>
        <div className="flex flex-wrap" style={{ gap: 6 }}>
          {lawyer.practice_areas.map((a) => <span className="chip" key={a.id}>{a.name}</span>)}
        </div>
        <div className="lawyer-meta">
          <span><i className="bi bi-award" /> {lawyer.experience_years} {t('years')}</span>
          <span><i className="bi bi-translate" /> {lawyer.languages}</span>
        </div>
      </div>
    </Link>
  );
}

export default function Lawyers() {
  const { t } = useLang();
  const { data, loading, error, reload } = useFetch('/api/lawyers/', { auth: false });
  return (
    <>
      <PageHero eyebrow={t('lawyers')} title={t('lawyersTitle')} text={t('lawyersSub')} crumbs={[{ label: t('lawyers') }]} />
      <section className="section">
        <div className="container">
          <ErrorBox error={error} onRetry={reload} />
          {loading ? <Spinner /> : (data?.results || []).length === 0 ? <Empty icon="bi-person-badge" title="No public lawyer profiles yet" /> : (
            <div className="grid grid-3">{data.results.map((l) => <LawyerCard key={l.id} lawyer={l} />)}</div>
          )}
        </div>
      </section>
    </>
  );
}

export function LawyerDetail() {
  const { id } = useParams();
  const { t } = useLang();
  const { data: l, loading, error } = useFetch(`/api/lawyers/${id}/`, { auth: false });
  if (loading) return <Spinner />;
  if (error) return <div className="container section"><ErrorBox error={error} /></div>;
  return (
    <>
      <PageHero eyebrow={l.title} title={l.full_name} crumbs={[{ label: t('lawyers'), to: '/lawyers' }, { label: l.full_name }]} />
      <section className="section">
        <div className="container split split-wide">
          <div>
            <h3>Profile</h3>
            <p className="lead" style={{ whiteSpace: 'pre-wrap' }}>{l.bio || '—'}</p>
            <h4 className="mt-3">{t('practice')}</h4>
            <div className="flex flex-wrap">
              {l.practice_areas.map((a) => <Link key={a.id} to={`/practice-areas/${a.slug}`} className="chip">{a.name}</Link>)}
            </div>
          </div>
          <div className="card">
            <div className="lawyer-photo" style={{ borderRadius: 12, marginBottom: 20 }}>
              {l.photo ? <img src={l.photo} alt={l.full_name} /> : <div className="monogram">{initials(l.full_name)}</div>}
            </div>
            <ul className="info-list">
              <li><i className="bi bi-award" /><div><strong>Experience</strong>{l.experience_years} {t('years')}</div></li>
              <li><i className="bi bi-translate" /><div><strong>{t('languages')}</strong>{l.languages}</div></li>
            </ul>
            <Link to="/consultation" className="btn btn-primary btn-block mt-2">{t('book')}</Link>
          </div>
        </div>
      </section>
    </>
  );
}
