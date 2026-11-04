import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../../api/client';
import { AreaIcon, Empty, ErrorBox, PageHero, Spinner } from '../../components/UI';
import { useLang } from '../../context/LangContext';
import { fmtDate } from '../../utils/format';
import { useFetch } from '../../utils/hooks';

function FaqItem({ faq }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card" style={{ padding: 0 }}>
      <button type="button" className="option-btn" style={{ border: 0, width: '100%' }} onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        {faq.question} <i className={`bi bi-chevron-${open ? 'up' : 'down'}`} />
      </button>
      {open && <div style={{ padding: '0 20px 20px' }}><p className="article-body mb-0">{faq.answer}</p><p className="small muted mt-2 mb-0">{faq.disclaimer}</p></div>}
    </div>
  );
}

function ArticleCard({ a }) {
  return (
    <Link to={`/knowledge/articles/${a.slug}`} className="card card-hover" style={{ color: 'inherit', display: 'block' }}>
      <div className="flex between mb-2"><span className="chip">{a.language === 'bn' ? 'বাংলা' : 'English'}</span>{a.is_sample && <span className="badge tone-amber">Sample</span>}</div>
      <h3>{a.title}</h3>
      <p className="muted small mb-0">{a.summary?.slice(0, 160)}</p>
    </Link>
  );
}

export default function Knowledge() {
  const { t, lang } = useLang();
  const [tab, setTab] = useState('articles');
  const [q, setQ] = useState('');
  const [results, setResults] = useState(null);
  const [searchErr, setSearchErr] = useState(null);
  const [language, setLanguage] = useState('');
  const langQ = language ? `?language=${language}` : '';
  const articles = useFetch(`/api/articles/${langQ}`, { auth: false });
  const faqs = useFetch(`/api/faqs/${langQ}`, { auth: false });
  const topics = useFetch('/api/rights-topics/', { auth: false });

  const search = async (e) => {
    e.preventDefault();
    if (!q.trim()) { setResults(null); return; }
    setSearchErr(null);
    try { setResults(await api.public(`/api/knowledge/search/?q=${encodeURIComponent(q.trim())}${language ? `&language=${language}` : ''}`)); } catch (err) { setSearchErr(err); }
  };

  return (
    <>
      <PageHero eyebrow={t('knowledge')} title={lang === 'bn' ? 'আপনার অধিকার জানুন' : 'Know your rights'} text={lang === 'bn' ? 'পর্যালোচিত প্রবন্ধ, প্রশ্নোত্তর ও নির্দেশিত সহায়তা।' : 'Reviewed articles, FAQs and guided help — in plain language.'} crumbs={[{ label: t('knowledge') }]} />
      <section className="section">
        <div className="container">
          <div className="flex between flex-wrap mb-2" style={{ gap: 16 }}>
            <form className="searchbar" style={{ flex: 1 }} onSubmit={search}>
              <i className="bi bi-search" style={{ alignSelf: 'center', marginLeft: 12, color: 'var(--muted)' }} />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={lang === 'bn' ? 'প্রবন্ধ ও প্রশ্নোত্তর খুঁজুন…' : 'Search articles and FAQs…'} />
              <button className="btn btn-primary btn-sm">{t('search')}</button>
            </form>
            <select className="input" style={{ width: 170 }} value={language} onChange={(e) => setLanguage(e.target.value)} aria-label="Content language">
              <option value="">All languages</option><option value="en">English</option><option value="bn">বাংলা</option>
            </select>
            <Link to="/knowledge/guided" className="btn btn-brass"><i className="bi bi-signpost-split" /> {t('guided')}</Link>
          </div>
          <ErrorBox error={searchErr} />
          {results && (
            <div className="mt-3">
              <div className="flex between"><h3>{results.count} result(s) for “{q}”</h3><button type="button" className="btn btn-ghost btn-sm" onClick={() => setResults(null)}>Clear</button></div>
              {results.results.length === 0 ? <Empty icon="bi-search" title="No matches" /> : (
                <div className="grid grid-3">{results.results.map((r) => (r.type === 'article' ? <ArticleCard key={`a${r.id}`} a={r} /> : <FaqItem key={`f${r.id}`} faq={r} />))}</div>
              )}
              <hr style={{ border: 0, borderTop: '1px solid var(--line)', margin: '36px 0' }} />
            </div>
          )}

          <div className="tabs mt-3">
            {[['articles', t('articles')], ['faqs', t('faqs')], ['topics', t('topics')]].map(([k, v]) => (
              <button key={k} type="button" className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{v}</button>
            ))}
          </div>

          {tab === 'articles' && (articles.loading ? <Spinner /> : (articles.data?.results || []).length === 0
            ? <Empty icon="bi-journal" title="No published articles yet">Articles appear here once reviewed and published by the firm.</Empty>
            : <div className="grid grid-3">{articles.data.results.map((a) => <ArticleCard key={a.id} a={a} />)}</div>)}
          {tab === 'faqs' && (faqs.loading ? <Spinner /> : (faqs.data?.results || []).length === 0
            ? <Empty icon="bi-question-circle" title="No published FAQs yet" />
            : <div className="grid" style={{ gap: 12 }}>{faqs.data.results.map((f) => <FaqItem key={f.id} faq={f} />)}</div>)}
          {tab === 'topics' && (topics.loading ? <Spinner /> : (topics.data?.results || []).length === 0
            ? <Empty icon="bi-bookmark" title="No topics yet" />
            : <div className="grid grid-3">{topics.data.results.map((tp) => (
              <div key={tp.id} className="card">
                <div className="icon-badge"><AreaIcon icon={tp.icon} fallback="bi-bookmark-star" /></div>
                <h3>{tp.title}</h3>
                <p className="muted small">{tp.description || '—'}</p>
              </div>
            ))}</div>)}
        </div>
      </section>
    </>
  );
}

export function ArticleDetail() {
  const { slug } = useParams();
  const { t } = useLang();
  const { data: a, loading, error } = useFetch(`/api/articles/${slug}/`, { auth: false });
  if (loading) return <Spinner />;
  if (error) return <div className="container section"><ErrorBox error={error} /></div>;
  return (
    <>
      <PageHero eyebrow={t('articles')} title={a.title} text={a.summary} crumbs={[{ label: t('knowledge'), to: '/knowledge' }, { label: a.title }]} />
      <section className="section">
        <div className="container" style={{ maxWidth: 820 }}>
          <div className="flex flex-wrap mb-2">
            {a.is_sample && <span className="badge tone-amber">Sample content</span>}
            {a.reviewed_at && <span className="small muted"><i className="bi bi-patch-check" /> Reviewed {fmtDate(a.reviewed_at)}</span>}
          </div>
          <div className="article-body">{a.body}</div>
          {a.source_reference && <p className="small muted mt-3"><strong>Source:</strong> {a.source_reference}</p>}
          <div className="notice mt-3">{a.disclaimer}</div>
          <div className="flex mt-3"><Link to="/knowledge" className="btn btn-ghost"><i className="bi bi-arrow-left" /> {t('knowledge')}</Link><Link to="/consultation" className="btn btn-primary">{t('book')}</Link></div>
        </div>
      </section>
    </>
  );
}

export function GuidedHelp() {
  const { t, lang } = useLang();
  const flows = useFetch('/api/guided-flows/', { auth: false });
  const [flow, setFlow] = useState(null);
  const [question, setQuestion] = useState(null);
  const [history, setHistory] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const call = async (fn) => { setBusy(true); setError(null); try { await fn(); } catch (e) { setError(e); } finally { setBusy(false); } };
  const start = (f) => call(async () => {
    const data = await api.public(`/api/guided-flows/${f.id}/start/`);
    setFlow(data.flow); setQuestion(data.question); setHistory([]); setResult(null);
  });
  const choose = (opt) => call(async () => {
    if (opt.next_question) {
      const q = await api.public(`/api/guided-questions/${opt.next_question}/`);
      setHistory((h) => [...h, question]); setQuestion(q);
    } else {
      setResult(await api.public(`/api/guided-options/${opt.id}/result/`));
    }
  });
  const back = () => { setResult(null); if (history.length) { setQuestion(history[history.length - 1]); setHistory((h) => h.slice(0, -1)); } };
  const reset = () => { setFlow(null); setQuestion(null); setResult(null); setHistory([]); };

  return (
    <>
      <PageHero eyebrow={t('guided')} title={lang === 'bn' ? 'ধাপে ধাপে সঠিক সহায়তা খুঁজুন' : 'Find the right help, step by step'} text={lang === 'bn' ? 'কয়েকটি সহজ প্রশ্নের উত্তর দিন। ফলাফল নির্দেশক মাত্র।' : 'Answer a few simple questions. Results are indicative only, not legal advice.'} crumbs={[{ label: t('knowledge'), to: '/knowledge' }, { label: t('guided') }]} />
      <section className="section">
        <div className="container" style={{ maxWidth: 760 }}>
          <ErrorBox error={error} />
          {!flow && (flows.loading ? <Spinner /> : (flows.data?.results || []).length === 0 ? <Empty icon="bi-signpost" title="No guided flows available" /> : (
            <div className="option-list">
              {flows.data.results.map((f) => (
                <button type="button" key={f.id} className="option-btn" onClick={() => start(f)} disabled={busy}>
                  <span><i className={`bi ${f.purpose === 'eligibility' ? 'bi-clipboard-check' : 'bi-compass'}`} style={{ marginRight: 10, color: 'var(--brass)' }} />{f.name}</span>
                  <i className="bi bi-arrow-right" />
                </button>
              ))}
            </div>
          ))}
          {flow && question && !result && (
            <div className="card reveal" key={question.id}>
              <div className="flex between mb-2"><span className="chip">{flow.name}</span><span className="small muted">Step {history.length + 1}</span></div>
              <h2>{question.text}</h2>
              <div className="option-list mt-2">
                {question.options.map((o) => (
                  <button key={o.id} type="button" className="option-btn" onClick={() => choose(o)} disabled={busy}>{o.label} <i className="bi bi-chevron-right" /></button>
                ))}
              </div>
              <div className="flex mt-3">
                {history.length > 0 && <button type="button" className="btn btn-ghost btn-sm" onClick={back}><i className="bi bi-arrow-left" /> Back</button>}
                <button type="button" className="btn btn-ghost btn-sm" onClick={reset}>Start over</button>
              </div>
            </div>
          )}
          {result && (
            <div className="card reveal">
              <div className="icon-badge brass"><i className="bi bi-lightbulb" /></div>
              <h2>{lang === 'bn' ? 'আপনার নির্দেশক ফলাফল' : 'Your indicative result'}</h2>
              <p className="lead">{result.message}</p>
              {result.practice_area && (
                <div className="card section-cream mt-2" style={{ border: 0 }}>
                  <span className="small muted">Suggested practice area</span>
                  <h3 className="mb-0"><Link to={`/practice-areas/${result.practice_area.slug}`}>{result.practice_area.name}</Link></h3>
                </div>
              )}
              {result.articles.map((a) => <p key={a.id} className="mt-2"><i className="bi bi-journal-text" /> <Link to={`/knowledge/articles/${a.slug}`}>{a.title}</Link></p>)}
              <div className="notice mt-2">{result.disclaimer}</div>
              <div className="flex flex-wrap mt-3">
                {result.escalate_to_consultation && <Link to={`/consultation${result.practice_area ? `?area=${result.practice_area.id}` : ''}`} className="btn btn-primary">{t('book')}</Link>}
                <Link to="/legal-aid" className="btn btn-outline">{t('legalAid')}</Link>
                <button type="button" className="btn btn-ghost" onClick={back}><i className="bi bi-arrow-left" /> Back</button>
                <button type="button" className="btn btn-ghost" onClick={reset}>Start over</button>
              </div>
            </div>
          )}
        </div>
      </section>
    </>
  );
}
