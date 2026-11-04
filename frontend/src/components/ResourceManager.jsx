import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import { useToast } from '../context/ToastContext';
import { fromLocalInput, toLocalInput } from '../utils/format';
import { useFetch } from '../utils/hooks';
import { Confirm, Empty, ErrorBox, Field, Modal, Pagination, Spinner } from './UI';

function buildQuery(params) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== '' && v != null) q.set(k, v); });
  const s = q.toString();
  return s ? `?${s}` : '';
}

/** Turn a field list + values into an API payload. */
export function toPayload(fields, values, { multipart, isEdit } = {}) {
  const out = multipart ? new FormData() : {};
  fields.forEach((f) => {
    if (f.readOnly || (isEdit && f.createOnly)) return;
    let v = values[f.name];
    if (f.type === 'file') { if (!v) return; }
    else if (f.type === 'datetime') v = v ? fromLocalInput(v) : null;
    else if (f.type === 'checkbox') v = !!v;
    else if (f.type === 'number') v = v === '' || v == null ? null : v;
    else if (v === '' && (f.nullable || f.type === 'select' || f.type === 'date')) v = null;
    if (v === undefined) return;
    if (f.omitEmpty && (v === null || v === '')) return;
    if (multipart) { if (v !== null) out.append(f.name, typeof v === 'boolean' ? String(v) : v); }
    else out[f.name] = v;
  });
  return out;
}

export function initialValues(fields, row, defaults = {}) {
  const v = {};
  fields.forEach((f) => {
    let value = row ? row[f.name] : (defaults[f.name] ?? f.default);
    if (f.type === 'datetime') value = toLocalInput(value);
    if (f.type === 'checkbox') value = !!value;
    if (value == null) value = f.type === 'checkbox' ? false : '';
    v[f.name] = value;
  });
  return v;
}

/** Generic create/edit form modal used across the dashboard. */
export function FormModal({ title, fields, row, defaults, endpoint, method, multipart, onClose, onSaved, submitText = 'Save', transform }) {
  const toast = useToast();
  const [values, setValues] = useState(() => initialValues(fields, row, defaults));
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const isEdit = !!row;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErrors({}); setError(null);
    try {
      let payload = toPayload(fields, values, { multipart, isEdit });
      if (transform) payload = transform(payload, values, isEdit);
      const url = isEdit ? `${endpoint}${row.id}/` : endpoint;
      const data = await api[method || (isEdit ? 'patch' : 'post')](url, payload);
      toast.success(isEdit ? 'Changes saved' : 'Created successfully');
      onSaved?.(data);
    } catch (err) {
      setErrors(err.fields || {});
      setError(err);
    } finally { setBusy(false); }
  };

  return (
    <Modal title={title} onClose={onClose} footer={(
      <>
        <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button type="submit" form="resource-form" className="btn btn-primary" disabled={busy}>{busy ? <Spinner small /> : submitText}</button>
      </>
    )}>
      <form id="resource-form" onSubmit={submit} className="form-grid" noValidate>
        {error && <div className="full"><ErrorBox error={error} /></div>}
        {fields.filter((f) => !(isEdit && f.createOnly) && !f.hidden).map((f) => (
          <Field key={f.name} {...f} type={f.type === 'datetime' ? 'datetime-local' : f.type}
            disabled={f.readOnly || (isEdit && f.lockOnEdit)}
            value={values[f.name]} error={errors[f.name]}
            onChange={(v) => setValues((s) => ({ ...s, [f.name]: v, ...(f.onChangeReset ? Object.fromEntries(f.onChangeReset.map((n) => [n, ''])) : {}) }))}
            options={typeof f.options === 'function' ? f.options(values) : f.options} />
        ))}
      </form>
    </Modal>
  );
}

/**
 * Paginated, filterable table with create / edit / delete for one API resource.
 */
export default function ResourceManager({
  title, endpoint, listPath, columns, fields, filters = [], baseQuery = {},
  canCreate = true, canEdit = () => true, canDelete = () => false, createLabel = 'Add new',
  rowActions, multipart, defaults, onRowClick, emptyText, transform, reloadKey, headExtra, onMutate,
}) {
  const toast = useToast();
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState(() => Object.fromEntries(filters.map((f) => [f.name, f.default ?? ''])));
  const [search, setSearch] = useState('');
  const [editing, setEditing] = useState(null); // row | 'new' | null
  const [deleting, setDeleting] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const searchFilter = filters.find((f) => f.type === 'search');
    if (!searchFilter) return undefined;
    const t = setTimeout(() => { setQuery((q) => ({ ...q, [searchFilter.name]: search })); setPage(1); }, 350);
    return () => clearTimeout(t);
  }, [search]); // eslint-disable-line react-hooks/exhaustive-deps

  const path = `${listPath || endpoint}${buildQuery({ ...baseQuery, ...query, page: page > 1 ? page : '' })}`;
  const { data, loading, error, reload } = useFetch(path, { deps: [reloadKey] });
  const rows = useMemo(() => (Array.isArray(data) ? data : data?.results || []), [data]);
  const fieldList = typeof fields === 'function' ? fields(editing === 'new' ? null : editing) : fields;

  const remove = async () => {
    setBusy(true);
    try {
      await api.del(`${endpoint}${deleting.id}/`);
      toast.success('Deleted');
      setDeleting(null);
      onMutate?.();
      reload();
    } catch (err) { toast.error(err.message); } finally { setBusy(false); }
  };

  return (
    <div className="panel">
      <div className="panel-head">
        <div className="toolbar">
          {title && <h3 style={{ marginRight: 8 }}>{title}</h3>}
          {filters.map((f) => (f.type === 'search' ? (
            <input key={f.name} className="input" placeholder={f.label || 'Search…'} value={search} onChange={(e) => setSearch(e.target.value)} />
          ) : (
            <select key={f.name} className="input" value={query[f.name]} onChange={(e) => { setQuery((q) => ({ ...q, [f.name]: e.target.value })); setPage(1); }}>
              <option value="">{f.label}</option>
              {(f.options || []).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          )))}
        </div>
        <div className="toolbar">
          {headExtra}
          <button type="button" className="icon-btn" onClick={reload} title="Refresh"><i className="bi bi-arrow-clockwise" /></button>
          {canCreate && fields && <button type="button" className="btn btn-primary btn-sm" onClick={() => setEditing('new')}><i className="bi bi-plus-lg" /> {createLabel}</button>}
        </div>
      </div>
      {error && <div className="panel-body"><ErrorBox error={error} onRetry={reload} /></div>}
      {loading && !data ? <Spinner /> : rows.length === 0 && !error ? <Empty title={emptyText || 'No records found'} /> : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                {columns.map((c) => <th key={c.key}>{c.label}</th>)}
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id ?? JSON.stringify(row)} style={onRowClick ? { cursor: 'pointer' } : undefined} onClick={onRowClick ? () => onRowClick(row) : undefined}>
                  {columns.map((c) => <td key={c.key} className={c.strong ? 'strong' : undefined}>{c.render ? c.render(row) : (row[c.key] ?? '—')}</td>)}
                  <td onClick={(e) => e.stopPropagation()}>
                    <div className="actions">
                      {rowActions?.(row, reload)}
                      {fields && canEdit(row) && <button type="button" className="icon-btn" title="Edit" onClick={() => setEditing(row)}><i className="bi bi-pencil" /></button>}
                      {canDelete(row) && <button type="button" className="icon-btn danger" title="Delete" onClick={() => setDeleting(row)}><i className="bi bi-trash3" /></button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pagination data={data} page={page} setPage={setPage} />

      {editing && (
        <FormModal
          title={editing === 'new' ? createLabel : `Edit ${title ? title.replace(/s$/, '').toLowerCase() : 'record'}`}
          fields={fieldList} row={editing === 'new' ? null : editing} defaults={defaults}
          endpoint={endpoint} multipart={multipart && editing === 'new'} transform={transform}
          onClose={() => setEditing(null)} onSaved={() => { setEditing(null); onMutate?.(); reload(); }} />
      )}
      {deleting && <Confirm danger title="Delete record" message="This cannot be undone. Continue?" confirmText="Delete" busy={busy} onConfirm={remove} onClose={() => setDeleting(null)} />}
    </div>
  );
}
