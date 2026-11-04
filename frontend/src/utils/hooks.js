import { useCallback, useEffect, useRef, useState } from 'react';
import { api, getAll } from '../api/client';
import { useLang } from '../context/LangContext';

/** Load data from an API path; re-runs when path or language changes. */
export function useFetch(path, { auth = true, deps = [] } = {}) {
  const { lang } = useLang();
  const [state, setState] = useState({ data: null, loading: !!path, error: null });
  const tick = useRef(0);

  const load = useCallback(async () => {
    if (!path) { setState({ data: null, loading: false, error: null }); return; }
    const id = ++tick.current;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = auth ? await api.get(path) : await api.public(path);
      if (id === tick.current) setState({ data, loading: false, error: null });
    } catch (error) {
      if (id === tick.current) setState({ data: null, loading: false, error });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, auth, lang, ...deps]);

  useEffect(() => { load(); }, [load]);
  return { ...state, reload: load };
}

// Shared lookup cache for dropdowns & name display in the dashboard.
const cache = {};
const LOOKUPS = {
  clients: '/api/clients/',
  practiceAreas: '/api/practice-areas/',
  users: '/api/users/',
  cases: '/api/cases/',
  invoices: '/api/invoices/',
};

export function invalidateLookup(...names) {
  names.forEach((n) => { delete cache[n]; });
}

export function useLookups(names) {
  const key = names.join(',');
  const [data, setData] = useState(() => Object.fromEntries(names.map((n) => [n, cache[n]?.value || []])));
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let alive = true;
    Promise.all(names.map(async (n) => {
      if (!cache[n]) cache[n] = { promise: getAll(LOOKUPS[n]).catch(() => []) };
      const value = await cache[n].promise;
      cache[n].value = value;
      return [n, value];
    })).then((entries) => { if (alive) setData(Object.fromEntries(entries)); });
    return () => { alive = false; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, version]);

  const refresh = useCallback(() => { invalidateLookup(...names); setVersion((v) => v + 1); }, [key]); // eslint-disable-line
  return { ...data, refresh };
}

export const byId = (list = [], id) => list.find((x) => String(x.id) === String(id));
