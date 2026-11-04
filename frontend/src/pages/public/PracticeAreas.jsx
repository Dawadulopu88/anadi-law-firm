import { Link, useOutletContext, useParams } from 'react-router-dom';
import { AreaIcon, ErrorBox, PageHero, Spinner } from '../../components/UI';
import { useLang } from '../../context/LangContext';
import { useFetch } from '../../utils/hooks';
import { AreaCard } from './Home';
import { LawyerCard } from './Lawyers';

export default function PracticeAreas() {
  const { t } = useLang();
  const { areas } = useOutletContext();
  return (
    <>
      <PageHero eyebrow={t('practice')} title={t('practiceTitle')} text={t('practiceSub')} crumbs={[{ label: t('practice') }]} />
      <section className="section">
        <div className="container">
          {areas.length === 0 ? <Spinner /> : <div className="grid grid-3">{areas.map((a, i) => <AreaCard key={a.id} area={a} index={i} />)}</div>}
        </div>
      </section>
    </>
  );
}

export function PracticeAreaDetail() {
  const { slug } = useParams();
  const { t } = useLang();
  const { data: area, loading, error } = useFetch(`/api/practice-areas/${slug}/`, { auth: false });
  const { data: lawyers } = useFetch('/api/lawyers/', { auth: false });
  if (loading) return <Spinner />;
  if (error) return <div className="container section"><ErrorBox error={error} /></div>;
  const team = (lawyers?.results || []).filter((l) => l.practice_areas.some((a) => a.slug === slug));
  return (
    <>
      <PageHero eyebrow={t('practice')} title={area.name} crumbs={[{ label: t('practice'), to: '/practice-areas' }, { label: area.name }]} />
      <section className="section">
        <div className="container split split-wide">
          <div>
            <div className="icon-badge brass"><AreaIcon icon={area.icon} /></div>
            <p className="lead" style={{ whiteSpace: 'pre-wrap' }}>{area.description}</p>
            <div className="notice mt-3">{t('disclaimer')}</div>
          </div>
          <div className="card">
            <h3>{t('ctaTitle')}</h3>
            <p className="muted">{t('ctaText')}</p>
            <Link to={`/consultation?area=${area.id}`} className="btn btn-primary btn-block">{t('book')}</Link>
            <Link to="/legal-aid" className="btn btn-ghost btn-block mt-2">{t('legalAid')}</Link>
          </div>
        </div>
      </section>
      {team.length > 0 && (
        <section className="section section-cream">
          <div className="container">
            <h2>{t('lawyersTitle')}</h2>
            <div className="grid grid-3 mt-3">{team.map((l) => <LawyerCard key={l.id} lawyer={l} />)}</div>
          </div>
        </section>
      )}
    </>
  );
}
