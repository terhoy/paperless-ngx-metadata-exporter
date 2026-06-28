
/* ── State ── */
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
  viewMode: localStorage.getItem('viewMode') || 'list',   // 'list' | 'tiles'
  labelPresets: {},
  // Visible columns: base fields + custom field ids
  visibleBase: JSON.parse(localStorage.getItem('visibleBase') || 'null'),
  visibleCF:   JSON.parse(localStorage.getItem('visibleCF')   || '[]'),
};

// Default visible base fields (no 'link' – title is the link)
const ALL_BASE = ['created','added','title','correspondent','document_type','tags','storage_path','link'];
const DEFAULT_BASE = ['created','title','correspondent','document_type','tags'];
if (!state.visibleBase) state.visibleBase = [...DEFAULT_BASE];

const $ = id => document.getElementById(id);

/* ── i18n helpers ── */
function tr(key, fallback) { return state.i18n[key] || fallback; }

/* ── Status card ── */
function setStatus(message, type = 'info', title = '') {
  const el = $('status');
  if (!el) return;
  el.className = `status-card ${type}`;
  el.innerHTML = `<span class="status-title">${title || (type === 'error' ? tr('error_title','Noe gikk galt') : tr('status_title','Status'))}</span><span class="status-body">${message}</span>`;
}

function friendlyErrorMessage(error) {
  const msg = String(error?.message || error || '');
  if (msg.includes('Kunne ikke koble til Paperless-ngx')) return tr('paperless_connection_error', msg);
  if (msg.includes('API-token'))   return tr('paperless_token_error', msg);
  if (msg.includes('Timeout'))     return tr('paperless_timeout_error', msg);
  return msg || tr('unknown_error', 'Ukjent feil.');
}

/* ── Fetch helpers ── */
async function api(path, opts = {}) {
  const r = await fetch(path, opts);
  const isJson = r.headers.get('content-type')?.includes('application/json');
  const data = isJson ? await r.json() : await r.blob();
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
}

async function downloadFileWithUiError(url, fallbackFilename) {
  try {
    setStatus(tr('export_preparing','Klargjør eksport...'), 'info', tr('status_title','Status'));
    const response = await fetch(url);
    if (!response.ok) {
      let message = response.statusText;
      try { const d = await response.json(); message = d.error || message; } catch (_) {}
      throw new Error(message);
    }
    const blob = await response.blob();
    let filename = fallbackFilename;
    const disposition = response.headers.get('Content-Disposition') || '';
    const match = disposition.match(/filename\*?=(?:UTF-8''|\")?([^\";\n]+)/i);
    if (match?.[1]) filename = decodeURIComponent(match[1].replace(/"/g,''));
    const url2 = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url2; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url2);
    setStatus(tr('export_ready','Eksporten er klar.'), 'success', tr('status_title','Status'));
  } catch (error) {
    setStatus(friendlyErrorMessage(error), 'error', tr('connection_error_title','Tilkoblingsfeil'));
  }
}

/* ── Date formatter ── */
const DATE_LOCALES = { nb:'nb-NO', en:'en-GB', de:'de-DE', fr:'fr-FR' };
function formatDate(isoStr) {
  if (!isoStr) return '';
  const [y,m,d] = isoStr.split('-').map(Number);
  if (!y||!m||!d) return isoStr;
  return new Date(y,m-1,d).toLocaleDateString(DATE_LOCALES[state.lang]||'nb-NO',{day:'2-digit',month:'2-digit',year:'numeric'});
}

/* ── Translations ── */
async function loadTranslations() {
  state.i18n = await api(`/api/translations/${state.lang}`);
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    if (state.i18n[key]) el.textContent = state.i18n[key];
  });
  document.documentElement.lang = state.lang;
  $('languageSelect').value = state.lang;
  $('delimiter').value = ['nb','de','fr'].includes(state.lang) ? ';' : ',';
  updateLabelPresetInfo();
}

/* ── Metadata ── */
function optionList(select, items, allLabel) {
  select.innerHTML = '';
  select.append(new Option(allLabel,''));
  select.append(new Option(state.i18n.empty||'(tom)','__empty__'));
  (items||[]).forEach(i => select.append(new Option(i.name||`#${i.id}`, i.id)));
}

async function loadMeta(force = false) {
  state.meta = await api(`/api/meta${force ? '?force=1' : ''}`);
  optionList($('correspondent'), state.meta.correspondents, state.i18n.all||'Alle');
  optionList($('documentType'),  state.meta.document_types,  state.i18n.all||'Alle');
  optionList($('storagePath'),   state.meta.storage_paths,   state.i18n.all||'Alle');
  optionList($('tag'),           state.meta.tags,            state.i18n.all||'Alle');
  buildColumnDropdown();
}

/* ── Column picker dropdown (Paperless-style) ── */
function buildColumnDropdown() {
  const menu = $('colDropdownMenu');
  if (!menu) return;
  menu.innerHTML = '';
  const labels = state.i18n.columns || {};

  // Base fields
  ALL_BASE.forEach(f => {
    const li = document.createElement('li');
    const label = document.createElement('label');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.dataset.field = f;
    cb.dataset.kind = 'base';
    cb.checked = state.visibleBase.includes(f);
    cb.onchange = onColToggle;
    label.append(cb, document.createTextNode(' ' + (labels[f] || f)));
    li.append(label);
    menu.append(li);
  });

  // Divider if there are custom fields
  if ((state.meta.custom_fields||[]).length > 0) {
    const div = document.createElement('li');
    div.className = 'col-divider';
    menu.append(div);
    (state.meta.custom_fields||[]).forEach(cf => {
      const li = document.createElement('li');
      const label = document.createElement('label');
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.dataset.field = String(cf.id);
      cb.dataset.kind = 'cf';
      cb.checked = state.visibleCF.includes(String(cf.id));
      cb.onchange = onColToggle;
      label.append(cb, document.createTextNode(' ' + (cf.name||`#${cf.id}`)));
      li.append(label);
      menu.append(li);
    });
  }
}

function onColToggle(e) {
  const cb = e.target;
  const field = cb.dataset.field;
  if (cb.dataset.kind === 'base') {
    if (cb.checked) {
      state.visibleBase = ALL_BASE.filter(f => {
        const el = document.querySelector(`#colDropdownMenu input[data-field="${f}"][data-kind="base"]`);
        return el ? el.checked : false;
      });
    } else {
      state.visibleBase = state.visibleBase.filter(f => f !== field);
    }
    localStorage.setItem('visibleBase', JSON.stringify(state.visibleBase));
  } else {
    if (cb.checked) { if (!state.visibleCF.includes(field)) state.visibleCF.push(field); }
    else { state.visibleCF = state.visibleCF.filter(f => f !== field); }
    localStorage.setItem('visibleCF', JSON.stringify(state.visibleCF));
  }
  if (state.docs.length) renderTable();
}

/* ── Label presets ── */
async function loadLabelPresets() {
  try {
    state.labelPresets = await api('/api/label-presets');
    const select = $('labelPreset');
    if (!select) return;
    const current = select.value;
    select.innerHTML = '';
    Object.entries(state.labelPresets).forEach(([key,preset]) => {
      select.append(new Option(preset.name||preset.description||key, key));
    });
    if (state.labelPresets[current]) select.value = current;
    updateLabelPresetInfo();
  } catch (_) {}
}

function updateLabelPresetInfo() {
  const select = $('labelPreset');
  const info = $('labelPresetInfo');
  if (!select||!info) return;
  const key = select.value;
  const preset = state.labelPresets[key];
  if (preset) {
    const rem = preset.removable ? ` · ${tr('removable','avtagbar')}` : '';
    info.textContent = `${preset.label_width_mm} x ${preset.label_height_mm} mm · ${preset.columns} x ${preset.rows} ${tr('labels_per_a4','etiketter per A4')}${rem}`;
  } else if (key==='avery_l4745rev_25') {
    info.textContent = `96 x 63,5 mm · 2 x 4 ${tr('labels_per_a4','etiketter per A4')} · ${tr('removable','avtagbar')}`;
  } else {
    info.textContent = `99 x 68 mm · 3 x 2 ${tr('labels_per_a4','etiketter per A4')}`;
  }
}

/* ── Query params ── */
function buildParams() {
  const p = new URLSearchParams();
  if ($('query').value.trim()) p.append('query', $('query').value.trim());
  const mapping = [['correspondent','correspondent'],['documentType','document_type'],['storagePath','storage_path']];
  for (const [id,apiName] of mapping) {
    const v = $(id).value;
    if (v === '__empty__') p.append(`${apiName}__isnull`,'1');
    else if (v) p.append(`${apiName}__id`, v);
  }
  if ($('tag').value === '__empty__') p.append('is_tagged','0');
  else if ($('tag').value) p.append('tags__id__all', $('tag').value);
  const df = $('dateField').value;
  if ($('fromDate').value) p.append(`${df}__date__gte`, $('fromDate').value);
  if ($('toDate').value)   p.append(`${df}__date__lte`, $('toDate').value);
  return p;
}

function buildArchiveParams() {
  const p = buildParams();
  if ($('caseId').value.trim())          p.append('case_id',     $('caseId').value.trim());
  if ($('caseTitle').value.trim())       p.append('case_title',  $('caseTitle').value.trim());
  if ($('caseDescription').value.trim()) p.append('description', $('caseDescription').value.trim());
  if ($('folder').value.trim())          p.append('folder',      $('folder').value.trim());
  if ($('labelPreset')?.value)           p.append('label_preset',$('labelPreset').value);
  if ($('xOffsetMm')?.value)             p.append('x_offset_mm', $('xOffsetMm').value);
  if ($('yOffsetMm')?.value)             p.append('y_offset_mm', $('yOffsetMm').value);
  return p;
}

/* ── Load documents ── */
async function loadDocs(page = 1) {
  state.page = page;
  const p = buildParams();
  p.append('page', page);
  p.append('page_size', state.pageSize);
  setStatus(tr('loading','Laster...'), 'info', tr('loading_title','Laster'));
  const data = await api('/api/documents?' + p.toString());
  state.docs   = data.results || [];
  state.count  = data.count   || 0;
  renderTable();
  setStatus(`${state.count} ${tr('documents_found','dokumenter funnet')}`, 'info', tr('status_title','Status'));
}

/* ── Table / Tiles rendering ── */
function cfById() {
  return Object.fromEntries((state.meta.custom_fields||[]).map(cf => [String(cf.id), cf]));
}

function docValue(d, key) {
  if (key.startsWith('cf:')) {
    const cf = (d.custom_fields||{})[key.slice(3)];
    return cf?.value ?? '';
  }
  if (key === 'created' || key === 'added') return formatDate(d[key]);
  return d[key] ?? '';
}

function renderTable() {
  if (state.viewMode === 'tiles') { renderTiles(); return; }

  const fields  = state.visibleBase;
  const cfIds   = state.visibleCF;
  const labels  = state.i18n.columns || {};
  const cfMap   = cfById();
  const colKeys = [...fields, ...cfIds.map(id => 'cf:' + id)];

  const thead = $('docsTable').querySelector('thead');
  const tbody = $('docsTable').querySelector('tbody');
  thead.innerHTML = '';
  tbody.innerHTML = '';
  $('docsTable').closest('.table-wrap').classList.remove('hidden');
  $('tilesContainer').classList.add('hidden');

  // Header
  const hr = document.createElement('tr');
  colKeys.forEach(key => {
    const th = document.createElement('th');
    const label = key.startsWith('cf:')
      ? (cfMap[key.slice(3)]?.name || key)
      : (labels[key] || key);
    // Sort indicator
    const sortIndicator = state.sortKey === key
      ? (state.sortDir === 'asc' ? ' ↑' : ' ↓') : '';
    th.textContent = label + sortIndicator;
    th.onclick = () => sortBy(key);
    hr.append(th);
  });
  thead.append(hr);

  // Rows
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
      } else if (f === 'link') {
        if (d.link) {
          const a = document.createElement('a');
          a.href = d.link; a.target = '_blank'; a.rel = 'noopener noreferrer';
          a.textContent = d.link;
          td.append(a);
        }
        td.title = d.link || '';
      } else if (f === 'created' || f === 'added') {
        td.textContent = formatDate(d[f]);
        td.title = d[f] || '';
      } else {
        td.textContent = d[f] || '';
        td.title = td.textContent;
      }
      tr.append(td);
    });
    cfIds.forEach(id => {
      const td = document.createElement('td');
      const cf = (d.custom_fields||{})[id];
      td.textContent = cf?.value ?? '';
      td.title = td.textContent;
      tr.append(td);
    });
    tbody.append(tr);
  });

  const totalPages = Math.max(1, Math.ceil(state.count / state.pageSize));
  $('pageInfo').textContent = `${state.page} / ${totalPages}`;
}

function renderTiles() {
  const cfMap = cfById();
  $('docsTable').closest('.table-wrap').classList.add('hidden');
  const container = $('tilesContainer');
  container.classList.remove('hidden');
  container.innerHTML = '';

  state.docs.forEach(d => {
    const card = document.createElement('div');
    card.className = 'tile-card';

    const titleRow = document.createElement('div');
    titleRow.className = 'tile-title';
    if (d.link) {
      const a = document.createElement('a');
      a.href = d.link; a.target = '_blank'; a.rel = 'noopener noreferrer';
      a.textContent = d.title || '—';
      titleRow.append(a);
    } else {
      titleRow.textContent = d.title || '—';
    }
    card.append(titleRow);

    const meta = document.createElement('div');
    meta.className = 'tile-meta';
    const show = state.visibleBase.filter(f => f !== 'title' && f !== 'link');
    const labels = state.i18n.columns || {};
    show.forEach(f => {
      const val = f === 'created' || f === 'added' ? formatDate(d[f]) : (d[f] || '');
      if (!val) return;
      const row = document.createElement('span');
      row.className = 'tile-meta-row';
      row.innerHTML = `<span class="tile-label">${labels[f]||f}:</span> ${val}`;
      meta.append(row);
    });
    state.visibleCF.forEach(id => {
      const cf = (d.custom_fields||{})[id];
      const val = cf?.value ?? '';
      if (!val && val !== 0) return;
      const row = document.createElement('span');
      row.className = 'tile-meta-row';
      row.innerHTML = `<span class="tile-label">${cfMap[id]?.name||id}:</span> ${val}`;
      meta.append(row);
    });
    card.append(meta);
    container.append(card);
  });

  const totalPages = Math.max(1, Math.ceil(state.count / state.pageSize));
  $('pageInfo').textContent = `${state.page} / ${totalPages}`;
}

/* ── Sort ── */
function sortBy(key) {
  state.sortDir = state.sortKey === key && state.sortDir === 'asc' ? 'desc' : 'asc';
  state.sortKey = key;
  const val = d => key.startsWith('cf:')
    ? ((d.custom_fields||{})[key.slice(3)]?.value ?? '')
    : (d[key] ?? '');
  state.docs.sort((a,b) => String(val(a)).localeCompare(String(val(b)), state.lang) * (state.sortDir==='asc'?1:-1));
  renderTable();
}

/* ── View mode toggle ── */
function setViewMode(mode) {
  state.viewMode = mode;
  localStorage.setItem('viewMode', mode);
  // Update button active states
  ['list','tiles'].forEach(m => {
    $(`viewBtn_${m}`)?.classList.toggle('active', m === mode);
  });
  if (state.docs.length) renderTable();
}

/* ── Export ── */
function exportParams(format) {
  const p = buildParams();
  p.append('format', format);
  p.append('delimiter', $('delimiter').value);
  state.visibleBase.forEach(f => p.append('fields', f));
  state.visibleCF.forEach(id => p.append('custom_field_ids', id));
  return p;
}

/* ── Column dropdown open/close ── */
function initColDropdown() {
  const btn  = $('colDropdownBtn');
  const menu = $('colDropdownMenu');
  if (!btn || !menu) return;
  btn.onclick = e => {
    e.stopPropagation();
    menu.classList.toggle('open');
  };
  document.addEventListener('click', e => {
    if (!menu.contains(e.target) && e.target !== btn) menu.classList.remove('open');
  });
}

/* ── Init ── */
async function init() {
  await loadTranslations();

  $('languageSelect').onchange = async e => {
    state.lang = e.target.value;
    localStorage.setItem('lang', state.lang);
    await loadTranslations();
    buildColumnDropdown();
    renderTable();
  };

  $('settingsBtn').onclick = () => $('settingsPanel').classList.toggle('hidden');
  $('toggleToken').onclick = () => { $('apiToken').type = $('apiToken').type === 'password' ? 'text' : 'password'; };
  $('saveSettings').onclick = async () => {
    await api('/api/settings', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({base_url:$('baseUrl').value, api_token:$('apiToken').value, default_language:$('defaultLanguage').value})
    });
    alert(tr('saved','Lagret'));
    location.reload();
  };
  $('testConnection').onclick = async () => {
    try {
      const r = await api('/api/test');
      setStatus(`OK: ${r.document_count}${r.demo_mode?' (demo)':''}`, 'success', tr('status_title','Status'));
    } catch (e) {
      setStatus(friendlyErrorMessage(e), 'error', tr('connection_error_title','Tilkoblingsfeil'));
    }
  };

  $('loadBtn').onclick   = () => loadDocs(1).catch(e => setStatus(friendlyErrorMessage(e),'error',tr('connection_error_title','Tilkoblingsfeil')));
  $('query').addEventListener('keydown', e => {
    if (e.key === 'Enter') loadDocs(1).catch(err => setStatus(friendlyErrorMessage(err),'error',tr('connection_error_title','Tilkoblingsfeil')));
  });
  $('refreshMeta').onclick = () => loadMeta(true).catch(e => setStatus(friendlyErrorMessage(e),'error',tr('connection_error_title','Tilkoblingsfeil')));
  $('resetBtn').onclick = () => {
    document.querySelectorAll('input').forEach(i => { if(i.type!=='checkbox') i.value=''; else i.checked=false; });
    document.querySelectorAll('select').forEach(s => { if(!['languageSelect','delimiter','dateField','labelPreset'].includes(s.id)) s.value=''; });
    $('xOffsetMm').value='0'; $('yOffsetMm').value='0';
    updateLabelPresetInfo();
  };

  $('prevPage').onclick = () => { if (state.page > 1) loadDocs(state.page-1); };
  $('nextPage').onclick = () => { if (state.page * state.pageSize < state.count) loadDocs(state.page+1); };

  $('csvBtn').onclick          = () => downloadFileWithUiError('/api/export?'                  + exportParams('csv').toString(),  'paperless_export.csv');
  $('xlsxBtn').onclick         = () => downloadFileWithUiError('/api/export?'                  + exportParams('xlsx').toString(), 'paperless_export.xlsx');
  $('contentSheetBtn').onclick = () => downloadFileWithUiError('/api/export/content-sheet?'    + buildArchiveParams().toString(), 'innholdsark.pdf');
  $('labelSheetBtn').onclick   = () => downloadFileWithUiError('/api/export/label-sheet?'      + buildArchiveParams().toString(), 'etiketter.pdf');
  $('archiveToggleBtn').onclick= () => $('archivePanel').classList.toggle('hidden');
  $('archiveCloseBtn').onclick = () => $('archivePanel').classList.add('hidden');
  $('combinedArchiveBtn').onclick = () => {
    const inc = $('includeContentSheet')?.checked;
    const inl = $('includeLabelSheet')?.checked;
    if (inc && inl)  downloadFileWithUiError('/api/export/archive-pdf?'   + buildArchiveParams().toString(), 'arkivpakke.pdf');
    else if (inc)    downloadFileWithUiError('/api/export/content-sheet?' + buildArchiveParams().toString(), 'innholdsark.pdf');
    else if (inl)    downloadFileWithUiError('/api/export/label-sheet?'   + buildArchiveParams().toString(), 'etiketter.pdf');
    else setStatus(tr('select_pdf_content','Velg minst én PDF-type.'), 'warning', tr('status_title','Status'));
  };
  $('labelPreset')?.addEventListener('change', updateLabelPresetInfo);

  // View mode buttons
  $('viewBtn_list')?.addEventListener('click',  () => setViewMode('list'));
  $('viewBtn_tiles')?.addEventListener('click', () => setViewMode('tiles'));
  setViewMode(state.viewMode); // restore saved mode

  initColDropdown();

  const settings = await api('/api/settings');
  $('baseUrl').value      = settings.base_url || '';
  $('defaultLanguage').value = settings.default_language || state.lang;
  if (settings.demo_mode) setStatus(tr('demo_mode','Demo-modus aktiv'), 'warning', tr('demo_mode_title','Demo-modus'));

  await loadLabelPresets();
  await loadMeta().catch(e => setStatus(friendlyErrorMessage(e),'error',tr('connection_error_title','Tilkoblingsfeil')));
}

init().catch(e => { setStatus(friendlyErrorMessage(e),'error',tr('error_title','Noe gikk galt')); });
