const state = {
  lang: localStorage.getItem('lang') || document.body.dataset.defaultLanguage || 'nb',
  i18n: {},
  meta: {},
  docs: [],
  page: 1,
  pageSize: 25,
  count: 0,
  sortKey: '',
  sortDir: 'asc',
  // Which base fields are visible (persisted in localStorage)
  visibleFields: JSON.parse(localStorage.getItem('visibleFields') || 'null'),
  // Column widths set by user drag (persisted)
  colWidths: JSON.parse(localStorage.getItem('colWidths') || '{}'),
};

const ALL_BASE_FIELDS = ['created','added','title','correspondent','document_type','tags','storage_path'];
if (!state.visibleFields) state.visibleFields = [...ALL_BASE_FIELDS];

/* ── Date formatter: uses Intl.DateTimeFormat per language ── */
const DATE_LOCALES = { nb: 'nb-NO', en: 'en-GB', de: 'de-DE', fr: 'fr-FR' };
function formatDate(isoStr) {
  if (!isoStr) return '';
  // isoStr is YYYY-MM-DD from the backend
  // Parse as local date to avoid UTC-offset shift
  const [y, m, d] = isoStr.split('-').map(Number);
  if (!y || !m || !d) return isoStr;
  const date = new Date(y, m - 1, d);
  const locale = DATE_LOCALES[state.lang] || 'nb-NO';
  return date.toLocaleDateString(locale, { day: '2-digit', month: '2-digit', year: 'numeric' });
}

const $ = id => document.getElementById(id);

async function api(path, opts={}) {
  const r = await fetch(path, opts);
  const data = r.headers.get('content-type')?.includes('application/json') ? await r.json() : await r.blob();
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
}

async function loadTranslations() {
  state.i18n = await api(`/api/translations/${state.lang}`);
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    if (state.i18n[key]) el.textContent = state.i18n[key];
  });
  $('languageSelect').value = state.lang;
  $('delimiter').value = ['nb','de','fr'].includes(state.lang) ? ';' : ',';
}

function optionList(select, items, allLabel) {
  select.innerHTML = '';
  select.append(new Option(allLabel, ''));
  select.append(new Option(state.i18n.empty || '(tom)', '__empty__'));
  (items || []).forEach(i => select.append(new Option(i.name || `#${i.id}`, i.id)));
}

async function loadMeta(force=false) {
  state.meta = await api(`/api/meta${force ? '?force=1' : ''}`);
  optionList($('correspondent'), state.meta.correspondents, state.i18n.all || 'Alle');
  optionList($('documentType'), state.meta.document_types, state.i18n.all || 'Alle');
  optionList($('storagePath'), state.meta.storage_paths, state.i18n.all || 'Alle');
  optionList($('tag'), state.meta.tags, state.i18n.all || 'Alle');
  renderCustomFieldCheckboxes();
  renderColumnPicker();
}

/* ── Custom field checkboxes (for displaying CF columns) ── */
function renderCustomFieldCheckboxes() {
  const box = $('customFieldChoices');
  box.innerHTML = '';
  (state.meta.custom_fields || []).forEach(cf => {
    const label = document.createElement('label');
    const cb = document.createElement('input');
    cb.type = 'checkbox'; cb.value = cf.id; cb.className = 'customField';
    label.append(cb, document.createTextNode(' ' + (cf.name || `#${cf.id}`)));
    box.append(label);
  });
}

/* ── Column picker panel ── */
function renderColumnPicker() {
  const box = $('columnPickerChoices');
  box.innerHTML = '';
  const labels = state.i18n.columns || {};
  ALL_BASE_FIELDS.forEach(f => {
    const label = document.createElement('label');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = f;
    cb.className = 'colPickerField';
    cb.checked = state.visibleFields.includes(f);
    cb.onchange = () => {
      if (cb.checked) {
        // insert in original order
        state.visibleFields = ALL_BASE_FIELDS.filter(x => {
          const el = box.querySelector(`input[value="${x}"]`);
          return el ? el.checked : false;
        });
      } else {
        state.visibleFields = state.visibleFields.filter(x => x !== f);
      }
      localStorage.setItem('visibleFields', JSON.stringify(state.visibleFields));
      if (state.docs.length) renderTable();
    };
    label.append(cb, document.createTextNode(' ' + (labels[f] || f)));
    box.append(label);
  });
}

function buildParams() {
  const p = new URLSearchParams();
  if ($('query').value.trim()) p.append('query', $('query').value.trim());
  const mapping = [['correspondent','correspondent'], ['documentType','document_type'], ['storagePath','storage_path']];
  for (const [id, apiName] of mapping) {
    const v = $(id).value;
    if (v === '__empty__') p.append(`${apiName}__isnull`, '1');
    else if (v) p.append(`${apiName}__id`, v);
  }
  if ($('tag').value === '__empty__') p.append('is_tagged', '0');
  else if ($('tag').value) p.append('tags__id__all', $('tag').value);
  const df = $('dateField').value;
  if ($('fromDate').value) p.append(`${df}__date__gte`, $('fromDate').value);
  if ($('toDate').value) p.append(`${df}__date__lte`, $('toDate').value);
  return p;
}

function selectedCustomFields() {
  return [...document.querySelectorAll('.customField:checked')].map(cb => cb.value);
}

async function loadDocs(page=1) {
  state.page = page;
  const p = buildParams();
  p.append('page', page); p.append('page_size', state.pageSize);
  $('status').textContent = state.i18n.loading || 'Laster...';
  const data = await api('/api/documents?' + p.toString());
  state.docs = data.results || []; state.count = data.count || 0;
  renderTable();
  $('status').textContent = `${state.count} ${state.i18n.documents_found || 'dokumenter funnet'}`;
}

/* ── Table rendering with resizable columns ── */
function renderTable() {
  const fields = state.visibleFields;
  const labels = state.i18n.columns || {};
  const cfs = selectedCustomFields();
  const cfById = Object.fromEntries((state.meta.custom_fields || []).map(cf => [String(cf.id), cf]));
  const thead = $('docsTable').querySelector('thead');
  const tbody = $('docsTable').querySelector('tbody');
  thead.innerHTML = ''; tbody.innerHTML = '';

  const colKeys = [...fields, ...cfs.map(id => 'cf:' + id)];

  // colgroup for width control
  let colgroup = $('docsTable').querySelector('colgroup');
  if (!colgroup) { colgroup = document.createElement('colgroup'); $('docsTable').prepend(colgroup); }
  colgroup.innerHTML = '';
  colKeys.forEach(key => {
    const col = document.createElement('col');
    const w = state.colWidths[key];
    if (w) col.style.width = w + 'px';
    colgroup.append(col);
  });

  const hr = document.createElement('tr');
  colKeys.forEach((key, colIdx) => {
    const th = document.createElement('th');
    const label = key.startsWith('cf:')
      ? (cfById[key.slice(3)]?.name || key)
      : (labels[key] || key);

    const span = document.createElement('span');
    span.textContent = label;
    span.className = 'th-label';
    span.onclick = () => sortBy(key);
    th.append(span);

    // Resize handle
    const handle = document.createElement('span');
    handle.className = 'col-resize-handle';
    handle.title = '';
    handle.onmousedown = e => startResize(e, colIdx, key, colgroup);
    th.append(handle);

    hr.append(th);
  });
  thead.append(hr);

  state.docs.forEach(d => {
    const tr = document.createElement('tr');
    fields.forEach(f => {
      const td = document.createElement('td');
      if (f === 'title') {
        if (d.link) {
          const a = document.createElement('a');
          a.href = d.link; a.target = '_blank'; a.rel = 'noopener noreferrer';
          a.textContent = d.title || '';
          td.append(a);
        } else {
          td.textContent = d.title || '';
        }
        td.title = d.title || '';
      } else if (f === 'created' || f === 'added') {
        td.textContent = formatDate(d[f]);
        td.title = d[f] || '';
      } else {
        td.textContent = d[f] || '';
        td.title = td.textContent;
      }
      tr.append(td);
    });
    cfs.forEach(id => {
      const td = document.createElement('td');
      const cf = (d.custom_fields || {})[id];
      td.textContent = cf?.value ?? '';
      td.title = td.textContent;
      tr.append(td);
    });
    tbody.append(tr);
  });

  const totalPages = Math.max(1, Math.ceil(state.count / state.pageSize));
  $('pageInfo').textContent = `${state.page} / ${totalPages}`;
}

/* ── Column resize logic ── */
function startResize(e, colIdx, key, colgroup) {
  e.preventDefault();
  e.stopPropagation();
  const col = colgroup.children[colIdx];
  const startX = e.clientX;
  const startW = col.offsetWidth || parseInt(state.colWidths[key] || '120', 10);

  const onMove = ev => {
    const newW = Math.max(40, startW + ev.clientX - startX);
    col.style.width = newW + 'px';
    state.colWidths[key] = newW;
  };
  const onUp = () => {
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
    localStorage.setItem('colWidths', JSON.stringify(state.colWidths));
  };
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
}

function sortBy(key) {
  const val = d => key.startsWith('cf:') ? ((d.custom_fields||{})[key.slice(3)]?.value ?? '') : (d[key] ?? '');
  state.sortDir = state.sortKey === key && state.sortDir === 'asc' ? 'desc' : 'asc';
  state.sortKey = key;
  state.docs.sort((a,b) => String(val(a)).localeCompare(String(val(b)), state.lang) * (state.sortDir === 'asc' ? 1 : -1));
  renderTable();
}

function download(format) {
  const p = buildParams();
  p.append('format', format);
  p.append('delimiter', $('delimiter').value);
  // Always include link in export even though it's not a visible column
  const exportFields = state.visibleFields.includes('link')
    ? state.visibleFields
    : [...state.visibleFields, 'link'];
  exportFields.forEach(f => p.append('fields', f));
  selectedCustomFields().forEach(id => p.append('custom_field_ids', id));
  window.location = '/api/export?' + p.toString();
}

async function init() {
  await loadTranslations();
  $('languageSelect').onchange = async e => {
    state.lang = e.target.value;
    localStorage.setItem('lang', state.lang);
    await loadTranslations();
    renderColumnPicker();
    renderTable();
  };
  $('settingsBtn').onclick = () => $('settingsPanel').classList.toggle('hidden');
  $('columnPickerBtn').onclick = () => $('columnPickerPanel').classList.toggle('hidden');
  $('toggleToken').onclick = () => { $('apiToken').type = $('apiToken').type === 'password' ? 'text' : 'password'; };
  $('saveSettings').onclick = async () => {
    await api('/api/settings', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({base_url: $('baseUrl').value, api_token: $('apiToken').value, default_language: $('defaultLanguage').value})
    });
    alert(state.i18n.saved || 'Lagret');
    location.reload();
  };
  $('testConnection').onclick = async () => {
    try { const r = await api('/api/test'); alert('OK: ' + r.document_count); }
    catch(e) { alert(e.message); }
  };
  $('resetColWidths').onclick = () => {
    state.colWidths = {};
    localStorage.removeItem('colWidths');
    if (state.docs.length) renderTable();
  };
  $('loadBtn').onclick = () => loadDocs(1).catch(e => $('status').textContent = e.message);
  $('refreshMeta').onclick = () => loadMeta(true).catch(e => $('status').textContent = e.message);
  $('resetBtn').onclick = () => {
    document.querySelectorAll('input').forEach(i => { if(i.type !== 'checkbox') i.value=''; else i.checked=false; });
    document.querySelectorAll('select').forEach(s => { if(!['languageSelect','delimiter','dateField'].includes(s.id)) s.value=''; });
  };
  $('prevPage').onclick = () => { if (state.page > 1) loadDocs(state.page-1); };
  $('nextPage').onclick = () => { if (state.page * state.pageSize < state.count) loadDocs(state.page+1); };
  $('csvBtn').onclick = () => download('csv');
  $('xlsxBtn').onclick = () => download('xlsx');

  const settings = await api('/api/settings');
  $('baseUrl').value = settings.base_url || '';
  $('defaultLanguage').value = settings.default_language || state.lang;
  await loadMeta().catch(e => $('status').textContent = e.message);
}
init().catch(e => { $('status').textContent = e.message; });
