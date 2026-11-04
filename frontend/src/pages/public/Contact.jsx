import { Link, useOutletContext } from 'react-router-dom';
import { Empty, PageHero } from '../../components/UI';
import { useLang } from '../../context/LangContext';
import { useFetch } from '../../utils/hooks';

export default function Contact() {
  const { t, lang } = useLang();
  const { firm } = useOutletContext();
  const { data: contacts } = useFetch('/api/help-contacts/', { auth: false });
  const list = contacts?.results || [];
  return (
    <>
      <PageHero eyebrow={t('contact')} title={lang === 'bn' ? 'আমাদের সাথে যোগাযোগ' : 'Get in touch'} text={lang === 'bn' ? 'আমরা সাহায্য করতে প্রস্তুত।' : 'We are here to help. Reach the firm directly or book a consultation.'} crumbs={[{ label: t('contact') }]} />
      <section className="section">
        <div className="container split">
          <div className="card">
            <img src="/logo-horizontal.png" alt="Anadi Law Firm" style={{ height: 56, marginBottom: 20 }} />
            <ul className="info-list">
              <li><i className="bi bi-geo-alt" /><div><strong>{t('address')}</strong>{firm?.address || '—'}</div></li>
              <li><i className="bi bi-telephone" /><div><strong>{t('phone')}</strong>{firm?.phone ? <a href={`tel:${firm.phone}`}>{firm.phone}</a> : '—'}</div></li>
              <li><i className="bi bi-envelope" /><div><strong>{t('email')}</strong>{firm?.email ? <a href={`mailto:${firm.email}`}>{firm.email}</a> : '—'}</div></li>
              <li><i className="bi bi-clock" /><div><strong>{t('hours')}</strong>{firm?.working_hours || '—'}</div></li>
            </ul>
            <Link to="/consultation" className="btn btn-primary mt-3">{t('book')}</Link>
          </div>
          <div>
            <div className="eyebrow">{lang === 'bn' ? 'সহায়তা নম্বর' : 'Support lines'}</div>
            <h2>{lang === 'bn' ? 'যাচাইকৃত সহায়তা যোগাযোগ' : 'Verified help contacts'}</h2>
            {list.length === 0 ? <Empty icon="bi-telephone-x" title="No verified contacts published yet">Only contacts verified by the firm are listed here.</Empty> : (
              <div className="grid" style={{ gap: 12 }}>
                {list.map((c) => (
                  <div key={c.id} className="card flex between" style={c.is_emergency ? { borderColor: '#e8c4bf' } : undefined}>
                    <div>
                      <h4 className="mb-0">{c.label} {c.is_emergency && <span className="badge tone-red">Emergency</span>}</h4>
                      <span className="small muted">{c.hours}</span>
                    </div>
                    <a href={`tel:${c.phone}`} className="btn btn-outline btn-sm"><i className="bi bi-telephone" /> {c.phone}</a>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>
    </>
  );
}
