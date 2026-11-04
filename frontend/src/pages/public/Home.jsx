import { Link, useOutletContext } from 'react-router-dom';
import { AreaIcon } from '../../components/UI';
import { useLang } from '../../context/LangContext';
import { useFetch } from '../../utils/hooks';
import { LawyerCard } from './Lawyers';

export function AreaCard({ area, index }) {
  const { t } = useLang();
  return (
    <Link to={`/practice-areas/${area.slug}`} className="card card-hover area-card">
      <span className="num">{String(index + 1).padStart(2, '0')}</span>
      <i className="bi bi-arrow-up-right arrow" />
      <div className="icon-badge"><AreaIcon icon={area.icon} /></div>
      <h3>{area.name}</h3>
      <p>{area.description || t('learnMore')}</p>
    </Link>
  );
}

export default function Home() {
  const { t, lang } = useLang();
  const { firm, areas } = useOutletContext();
  const { data: lawyers } = useFetch('/api/lawyers/', { auth: false });
  const { data: courses } = useFetch('/api/courses/', { auth: false });
  const lawyerList = lawyers?.results || [];
  const bn = lang === 'bn';

  const values = bn ? [
    ['bi-shield-check', 'গোপনীয়তা ও আস্থা', 'আপনার তথ্য সুরক্ষিত, ভূমিকাভিত্তিক অ্যাক্সেস ও ব্যক্তিগত ডকুমেন্ট স্টোরেজ।'],
    ['bi-translate', 'দ্বিভাষিক সেবা', 'বাংলা ও ইংরেজিতে পরামর্শ, নথি ও যোগাযোগ।'],
    ['bi-laptop', 'ক্লায়েন্ট পোর্টাল', 'মামলা, শুনানি, ডকুমেন্ট ও ইনভয়েস এক জায়গায় দেখুন।'],
    ['bi-heart', 'আইনি সহায়তা', 'যাদের প্রয়োজন তাদের জন্য সহজ আবেদন ও গোপন ট্র্যাকিং।'],
  ] : [
    ['bi-shield-check', 'Confidential by design', 'Role-based access and private document storage keep your matter protected.'],
    ['bi-translate', 'Bilingual counsel', 'Consultations, documents and updates in Bangla and English.'],
    ['bi-laptop', 'Client portal', 'Follow your cases, hearings, documents and invoices in one place.'],
    ['bi-heart', 'Access to justice', 'A simple legal-aid application with private, code-based tracking.'],
  ];

  return (
    <>
      <section className="hero">
        <div className="container">
          <div className="reveal">
            <div className="eyebrow">{t('heroEyebrow')}</div>
            <h1>{t('heroTitle')}<br /><em>{t('heroTitle2')}</em></h1>
            <p className="lead">{t('heroText')}</p>
            <div className="hero-actions">
              <Link to="/consultation" className="btn btn-brass"><i className="bi bi-calendar-check" /> {t('book')}</Link>
              <Link to="/knowledge/guided" className="btn btn-ghost-light"><i className="bi bi-signpost-split" /> {t('findHelp')}</Link>
            </div>
            <div className="hero-stats">
              <div><strong>{areas.length || '—'}</strong><span>{t('practice')}</span></div>
              <div><strong>{lawyerList.length || '—'}</strong><span>{t('lawyers')}</span></div>
              <div><strong>2</strong><span>{bn ? 'ভাষা' : 'Languages'}</span></div>
              <div><strong>24/7</strong><span>{bn ? 'অনলাইন পোর্টাল' : 'Online portal'}</span></div>
            </div>
          </div>
          <div className="hero-mark"><img src="/logo-vertical-light.png" alt="" /></div>
        </div>
      </section>

      <section className="section">
        <div className="container split split-wide" style={{ alignItems: 'center' }}>
          <div>
            <div className="eyebrow">{bn ? 'আমাদের সম্পর্কে' : 'About the firm'}</div>
            <h2>{firm?.name || 'Anadi Law Firm'}</h2>
            <p className="lead">{firm?.about || t('heroText')}</p>
            <p className="quote mt-3">“{bn ? 'ন্যায়ের পথে, প্রতিটি পদক্ষেপে আপনার পাশে।' : 'Beside you at every step on the path to justice.'}”</p>
          </div>
          <div className="grid" style={{ gap: 22 }}>
            {values.map(([icon, title, text]) => (
              <div className="value" key={title}>
                <div className="icon-badge"><i className={`bi ${icon}`} /></div>
                <div><h4>{title}</h4><p>{text}</p></div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section section-cream">
        <div className="container">
          <div className="section-head">
            <div>
              <div className="eyebrow">{t('practice')}</div>
              <h2 className="mb-0">{t('practiceTitle')}</h2>
            </div>
            <p>{t('practiceSub')}</p>
          </div>
          <div className="grid grid-3">
            {areas.slice(0, 6).map((a, i) => <AreaCard key={a.id} area={a} index={i} />)}
          </div>
          <div className="center mt-3"><Link to="/practice-areas" className="btn btn-outline">{t('viewAll')} <i className="bi bi-arrow-right" /></Link></div>
        </div>
      </section>

      {lawyerList.length > 0 && (
        <section className="section">
          <div className="container">
            <div className="section-head">
              <div>
                <div className="eyebrow">{t('lawyers')}</div>
                <h2 className="mb-0">{t('lawyersTitle')}</h2>
              </div>
              <Link to="/lawyers" className="btn btn-ghost">{t('viewAll')} <i className="bi bi-arrow-right" /></Link>
            </div>
            <div className="grid grid-3">{lawyerList.slice(0, 3).map((l) => <LawyerCard key={l.id} lawyer={l} />)}</div>
          </div>
        </section>
      )}

      <section className="section section-dark">
        <div className="container split" style={{ alignItems: 'center' }}>
          <div>
            <div className="eyebrow">{t('legalAid')}</div>
            <h2>{t('legalAidTitle')}</h2>
            <p style={{ color: 'rgba(246,241,228,.75)' }} className="lead">{t('legalAidText')}</p>
            <div className="hero-actions">
              <Link to="/legal-aid" className="btn btn-brass">{t('apply')}</Link>
              <Link to="/legal-aid/track" className="btn btn-ghost-light">{t('track')}</Link>
            </div>
          </div>
          <div className="grid grid-2">
            {[
              ['bi-signpost-split', t('guided'), '/knowledge/guided'],
              ['bi-journal-text', t('knowledge'), '/knowledge'],
              ['bi-mortarboard', t('academy'), '/academy'],
              ['bi-telephone', t('contact'), '/contact'],
            ].map(([icon, text, to]) => (
              <Link key={to} to={to} className="card card-hover" style={{ background: 'rgba(246,241,228,.05)', borderColor: 'rgba(190,206,169,.18)', color: 'var(--cream)' }}>
                <i className={`bi ${icon}`} style={{ fontSize: '1.6rem', color: 'var(--sage-400)' }} />
                <h4 style={{ color: 'var(--cream)', margin: '12px 0 0' }}>{text}</h4>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {(courses?.results || []).length > 0 && (
        <section className="section">
          <div className="container">
            <div className="section-head">
              <div><div className="eyebrow">{t('academy')}</div><h2 className="mb-0">{bn ? 'শিখুন ও সচেতন হোন' : 'Learn your rights'}</h2></div>
              <Link to="/academy" className="btn btn-ghost">{t('viewAll')} <i className="bi bi-arrow-right" /></Link>
            </div>
            <div className="grid grid-3">
              {courses.results.slice(0, 3).map((c) => (
                <div key={c.id} className="card card-hover">
                  <div className="flex between mb-2"><span className="chip">{c.level}</span><span className="small muted"><i className="bi bi-clock" /> {c.duration}</span></div>
                  <h3>{c.title}</h3>
                  <p className="muted small">{c.summary}</p>
                  <div className="small"><i className="bi bi-person-video3" /> {c.instructor}</div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="section-sm">
        <div className="container">
          <div className="cta-band">
            <div>
              <h2>{t('ctaTitle')}</h2>
              <p>{t('ctaText')}</p>
            </div>
            <div className="flex flex-wrap">
              <Link to="/consultation" className="btn btn-brass">{t('book')}</Link>
              {firm?.phone && <a href={`tel:${firm.phone}`} className="btn btn-ghost-light"><i className="bi bi-telephone" /> {firm.phone}</a>}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
