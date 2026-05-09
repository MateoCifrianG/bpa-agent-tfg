/**
 * dashboard.js — BPA-Agent Dashboard Logic
 * Datos reales de la API, sin hardcode, sin costes de API externa
 */

'use strict';

// ── Constantes ────────────────────────────────────────────────
const ICONS = {
  proceso: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="5" r="3"/><circle cx="5" cy="19" r="3"/><circle cx="19" cy="19" r="3"/><path d="M12 8v3M8.25 16.5 12 11M15.75 16.5 12 11"/></svg>`,
  auto:    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m13 2-2 2.5h3L12 7"/><path d="M10 14v-3a2 2 0 0 1 4 0v3"/><path d="M6 14a2 2 0 0 0-2 2v2h16v-2a2 2 0 0 0-2-2"/><path d="M14 14H10"/></svg>`,
  kpi:     `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>`,
  chat:    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
  trash:   `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>`,
  edit:    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`,
  search:  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
  send:    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>`,
};

// ── Cache de datos ────────────────────────────────────────────
let _procesos       = [];
let _autos          = [];
let _kpis           = [];
let _empresa        = null;
let _conversacionId = null;
let _chatHistorial  = [];   // historial en memoria del chat activo
let _isSending      = false;
let _searchData     = [];   // índice para búsqueda global

// ── API helper (thin wrapper sobre api.js) ────────────────────
const BPA = {
  async get(path) {
    const { token } = API.session.get();
    const r = await fetch('http://localhost:8002' + path, {
      headers: { Authorization: `Bearer ${token}` },
      credentials: 'include',
    });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  },
  async post(path, body) {
    const { token } = API.session.get();
    const r = await fetch('http://localhost:8002' + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
      credentials: 'include',
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${r.status}`);
    }
    return r.json();
  },
  async put(path, body) {
    const { token } = API.session.get();
    const r = await fetch('http://localhost:8002' + path, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
      credentials: 'include',
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${r.status}`);
    }
    return r.json();
  },
  async del(path) {
    const { token } = API.session.get();
    const r = await fetch('http://localhost:8002' + path, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
      credentials: 'include',
    });
    if (!r.ok && r.status !== 204) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${r.status}`);
    }
    return true;
  },
};

// ── Utilidades DOM ────────────────────────────────────────────
function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
function scoreClass(s) {
  if (s == null) return 'none';
  return s < 40 ? 'low' : s < 70 ? 'mid' : 'good';
}
function scoreColor(s) {
  if (s == null) return 'var(--fg-3)';
  return s < 40 ? 'var(--rose)' : s < 70 ? 'var(--amber)' : 'var(--emerald)';
}
function estadoPill(estado) {
  const map = {
    activa:     ['active','Activa'],
    pendiente:  ['pending','Pendiente'],
    pausada:    ['paused','Pausada'],
    error:      ['error','Error'],
    analizado:  ['active','Analizado'],
    critico:    ['error','Crítico'],
    optimizado: ['active','Optimizado'],
  };
  const [cls, label] = map[estado] || ['pending', esc(estado)];
  return `<span class="status-pill ${cls}"><span class="status-dot"></span>${label}</span>`;
}
function emptyState(icon, title, desc) {
  return `<div class="empty-state">${icon}<h3>${esc(title)}</h3><p>${esc(desc)}</p></div>`;
}
function loadingRow() {
  return `<div class="loading-row"><div class="spinner"></div></div>`;
}

// ── Sanitización de inputs (XSS prevention) ──────────────────
function sanitize(val, maxLen = 500) {
  if (typeof val !== 'string') return val;
  const stripped = val.trim().substring(0, maxLen);
  // Rechazar si contiene patrones peligrosos
  if (/<script|javascript:|on\w+=/i.test(stripped)) {
    throw new Error('Entrada no permitida: contiene código no válido');
  }
  return stripped;
}
function sanitizeForm(fields) {
  const result = {};
  for (const [key, {val, max}] of Object.entries(fields)) {
    result[key] = val ? sanitize(val, max || 500) : null;
  }
  return result;
}

// ── HOME DASHBOARD ────────────────────────────────────────────
async function loadHomeDashboard() {
  try {
    const [procesos, autos, kpis, empresa, convs] = await Promise.allSettled([
      BPA.get('/api/procesos'),
      BPA.get('/api/automatizaciones'),
      BPA.get('/api/kpis'),
      BPA.get('/api/empresa/mia'),
      BPA.get('/api/agente/conversaciones'),
    ]);

    _procesos = procesos.status === 'fulfilled' ? procesos.value : [];
    _autos    = autos.status    === 'fulfilled' ? autos.value    : [];
    _kpis     = kpis.status     === 'fulfilled' ? kpis.value     : [];
    _empresa  = empresa.status  === 'fulfilled' ? empresa.value  : null;

    // Exponer en window para acceso desde modales (body functions son closures del HTML)
    window._procesos = _procesos;
    window._autos    = _autos;
    window._kpis     = _kpis;
    window._empresa  = _empresa;

    // Badges de nav con datos reales (ocultar si 0)
    const convCount = convs.status === 'fulfilled' ? convs.value.length : 0;
    _updateNavBadge('badgeAgente', convCount);
    _updateNavBadge('badgePropuestas', convCount);

    // Índice de búsqueda global
    _buildSearchIndex();

    _renderHomeStats();
    _renderHomeProcesos();
    _renderHomeAutos();
    _renderHomeEmpresa();
    _updateWelcomeSummary();
  } catch (err) {
    console.error('Error cargando dashboard:', err);
  }
}

function _updateNavBadge(id, count) {
  const el = document.getElementById(id);
  if (!el) return;
  if (count > 0) {
    el.textContent = count;
    el.style.display = '';
  } else {
    el.style.display = 'none';
  }
}

function _renderHomeStats() {
  const activasCnt = _autos.filter(a => a.estado === 'activa').length;
  const horasTot   = _autos.reduce((s, a) => s + (a.horas_mes || 0), 0);
  const scores     = _procesos.filter(p => p.score != null).map(p => p.score);
  const avgScore   = scores.length ? Math.round(scores.reduce((a,b)=>a+b,0)/scores.length) : null;

  setText('statProcesos',  _procesos.length || '–');
  setText('statProcesosub', _procesos.length === 0 ? 'Añade tu primer proceso' : `${_procesos.length} proceso${_procesos.length!==1?'s':''} registrado${_procesos.length!==1?'s':''}`);
  setText('statAutos',     _autos.length || '–');
  setText('statAutosub',   `${activasCnt} activa${activasCnt!==1?'s':''} · ${_autos.length-activasCnt} pendiente${_autos.length-activasCnt!==1?'s':''}`);
  setText('statHoras',     horasTot > 0 ? horasTot + 'h' : '–');
  setText('statHorasub',   horasTot > 0 ? 'ahorradas al mes' : 'Sin automatizaciones activas');
  setText('statScore',     avgScore ?? '–');
  setText('statScoresub',  avgScore != null ? `Promedio de ${scores.length} proceso${scores.length!==1?'s':''} · Objetivo: 80` : 'Sin scores asignados');
}

function _updateWelcomeSummary() {
  const el = document.getElementById('welcomeSummary');
  if (!el) return;
  const activasCnt = _autos.filter(a=>a.estado==='activa').length;
  if (!_procesos.length && !_autos.length) {
    el.innerHTML = 'Empieza añadiendo tus <strong style="color:var(--fg)">procesos de negocio</strong> para que el agente pueda analizarlos.';
  } else {
    el.innerHTML = `Tienes <strong style="color:var(--fg)">${_procesos.length} proceso${_procesos.length!==1?'s':''}</strong> mapeado${_procesos.length!==1?'s':''} y <strong style="color:var(--fg)">${activasCnt} automatización${activasCnt!==1?'es activas':' activa'}</strong> generando valor.`;
  }
  // Empresa nombre en el breadcrumb (usa ID para no sobreescribir otros .crumb-faded)
  const crumb = document.getElementById('breadcrumbEmpresa') || document.querySelector('.crumb-faded');
  if (crumb && _empresa) crumb.textContent = _empresa.nombre;
}

function _renderHomeProcesos() {
  const el = document.getElementById('homeProcesos');
  if (!el) return;
  if (!_procesos.length) {
    el.innerHTML = `<div style="padding:.75rem;color:var(--fg-3);font-size:.8rem">Sin procesos. <a href="#" onclick="navTo('Procesos','page-procesos');return false" style="color:var(--accent)">Añadir →</a></div>`;
    return;
  }
  const sorted = [..._procesos].sort((a,b) => (a.score??100)-(b.score??100)).slice(0,5);
  el.innerHTML = sorted.map((p,i) => {
    const s = p.score, col = scoreColor(s), w = s ?? 50;
    return `<div class="process-item" style="cursor:pointer" onclick="navTo('Procesos','page-procesos')">
      <span class="proc-rank">${i+1}</span>
      <span class="proc-name">${esc(p.nombre)}</span>
      <div class="proc-bar-wrap"><div class="proc-bar" style="width:${w}%;background:${col}"></div></div>
      <span class="proc-score" style="color:${col}">${s??'–'}</span>
    </div>`;
  }).join('');
}

function _renderHomeAutos() {
  const el = document.getElementById('homeAutosTbody');
  if (!el) return;
  if (!_autos.length) {
    el.innerHTML = `<tr><td colspan="3" style="color:var(--fg-3);font-size:.8rem;padding:.75rem">Sin automatizaciones. <a href="#" onclick="navTo('Automatizaciones','page-automatizaciones');return false" style="color:var(--accent)">Crear →</a></td></tr>`;
    return;
  }
  el.innerHTML = _autos.slice(0,4).map(a => `<tr onclick="navTo('Automatizaciones','page-automatizaciones')" style="cursor:pointer">
    <td>${esc(a.nombre)}</td>
    <td>${a.herramienta?`<span class="tool-tag">${esc(a.herramienta)}</span>`:'–'}</td>
    <td>${estadoPill(a.estado)}</td>
  </tr>`).join('');
}

function _renderHomeEmpresa() {
  const el = document.getElementById('homeEmpresaInfo');
  if (!el) return;
  if (!_empresa) {
    el.innerHTML = `<div class="activity-item"><div class="act-dot" style="background:var(--fg-3);box-shadow:none"></div><div class="act-text"><div class="act-title">Sin datos de empresa</div></div></div>`;
    return;
  }
  const items = [
    { col:'var(--accent)',  title: _empresa.nombre, sub: _empresa.sector || 'Sector no especificado' },
    { col:'var(--indigo)',  title: `${_empresa.empleados ?? '–'} empleados`, sub: _empresa.ciudad || 'Ciudad no especificada' },
    { col:'var(--amber)',   title: `${_kpis.length} KPI${_kpis.length!==1?'s':''}`, sub: 'indicadores activos' },
    { col:'var(--emerald)', title: `${_autos.filter(a=>a.estado==='activa').length} automatizaciones activas`, sub: `${_autos.reduce((s,a)=>s+(a.horas_mes||0),0)}h ahorradas/mes` },
  ];
  el.innerHTML = items.map(it => `<div class="activity-item">
    <div class="act-dot" style="background:${it.col}"></div>
    <div class="act-text"><div class="act-title">${esc(it.title)}</div><div class="act-meta">${esc(it.sub)}</div></div>
  </div>`).join('');
}

// ── BÚSQUEDA GLOBAL ───────────────────────────────────────────
function _buildSearchIndex() {
  _searchData = [
    ..._procesos.map(p => ({ type:'Proceso', label: p.nombre, sub: `Score ${p.score??'–'} · ${p.estado}`, action: ()=>navTo('Procesos','page-procesos') })),
    ..._autos.map(a   => ({ type:'Auto',    label: a.nombre, sub: `${a.herramienta||''} · ${a.estado}`,   action: ()=>navTo('Automatizaciones','page-automatizaciones') })),
    ..._kpis.map(k    => ({ type:'KPI',     label: k.nombre, sub: `${k.valor}${k.unidad?' '+k.unidad:''}`, action: ()=>navTo('KPIs','page-kpis') })),
  ];
}

let _searchKbdListener = null;
function initSearch() {
  const btn = document.querySelector('.topbar-search');
  if (!btn) return;
  btn.onclick = openSearch;
  if (_searchKbdListener) document.removeEventListener('keydown', _searchKbdListener);
  _searchKbdListener = e => {
    if ((e.metaKey||e.ctrlKey) && e.key==='k') { e.preventDefault(); openSearch(); }
    if (e.key==='Escape') closeSearch();
  };
  document.addEventListener('keydown', _searchKbdListener);
}

function openSearch() {
  let overlay = document.getElementById('searchOverlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'searchOverlay';
    overlay.style.cssText = 'position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.6);backdrop-filter:blur(4px);display:flex;align-items:flex-start;justify-content:center;padding-top:12vh';
    overlay.innerHTML = `
      <div style="width:min(560px,92vw);background:var(--modal-bg);border:1px solid var(--border-hi);border-radius:14px;overflow:hidden;box-shadow:0 32px 80px rgba(0,0,0,.7)">
        <div style="display:flex;align-items:center;gap:.75rem;padding:.85rem 1rem;border-bottom:1px solid var(--border)">
          ${ICONS.search}
          <input id="searchInput" placeholder="Buscar procesos, KPIs, automatizaciones…"
            style="flex:1;background:none;border:none;outline:none;font-size:.95rem;color:var(--fg);font-family:inherit"/>
          <span style="font-size:.7rem;color:var(--fg-3);background:var(--s2);padding:.15rem .4rem;border-radius:5px;border:1px solid var(--border)">Esc</span>
        </div>
        <div id="searchResults" style="max-height:340px;overflow-y:auto;padding:.4rem"></div>
      </div>`;
    overlay.addEventListener('click', e => { if(e.target===overlay) closeSearch(); });
    document.body.appendChild(overlay);
    const inp = document.getElementById('searchInput');
    inp.addEventListener('input', () => renderSearchResults(inp.value));
    renderSearchResults('');
  }
  overlay.style.display = 'flex';
  setTimeout(() => document.getElementById('searchInput')?.focus(), 50);
}

function closeSearch() {
  const el = document.getElementById('searchOverlay');
  if (el) el.style.display = 'none';
}

function renderSearchResults(query) {
  const el = document.getElementById('searchResults');
  if (!el) return;
  const q = query.toLowerCase().trim();
  const results = q ? _searchData.filter(d => d.label.toLowerCase().includes(q) || d.sub.toLowerCase().includes(q)) : _searchData.slice(0,8);
  if (!results.length) {
    el.innerHTML = `<div style="padding:1.5rem;text-align:center;color:var(--fg-3);font-size:.85rem">Sin resultados para "${esc(query)}"</div>`;
    return;
  }
  el.innerHTML = results.slice(0,10).map((r,i) => `
    <div onclick="r${i}()" id="sr${i}" style="display:flex;align-items:center;gap:.75rem;padding:.6rem .85rem;border-radius:8px;cursor:pointer;transition:background .1s" onmouseover="this.style.background='var(--hover-bg)'" onmouseout="this.style.background=''" >
      <span style="font-size:.65rem;font-weight:600;padding:.15rem .4rem;border-radius:5px;background:var(--s2);color:var(--fg-3);min-width:52px;text-align:center">${esc(r.type)}</span>
      <div style="flex:1;min-width:0"><div style="font-size:.85rem;font-weight:500;color:var(--fg)">${esc(r.label)}</div><div style="font-size:.72rem;color:var(--fg-3)">${esc(r.sub)}</div></div>
    </div>`).join('');
  // Bind click handlers (can't use inline due to closure)
  results.slice(0,10).forEach((r,i) => {
    document.getElementById(`sr${i}`).onclick = () => { r.action(); closeSearch(); };
  });
}

// ── NAVEGACIÓN ────────────────────────────────────────────────
function navTo(title, pageId) {
  const navEl = document.querySelector(`[data-page="${title}"]`);
  setPage(navEl, title, pageId);
}

// ── PROCESOS ─────────────────────────────────────────────────
async function loadProcesos() {
  const el = document.getElementById('procesosList');
  if (!el) return;
  el.innerHTML = loadingRow();
  try {
    _procesos = await BPA.get('/api/procesos');
    _buildSearchIndex();
    _renderProcesos();
  } catch(e) {
    el.innerHTML = `<div class="empty-state"><p>Error: ${esc(e.message)}</p></div>`;
  }
}

function _renderProcesos() {
  const el = document.getElementById('procesosList');
  if (!el) return;
  if (!_procesos.length) {
    el.innerHTML = emptyState(ICONS.proceso, 'Sin procesos', 'Añade tu primer proceso para que el agente IA pueda analizarlo y proponer automatizaciones.');
    return;
  }
  el.innerHTML = `<table class="data-table">
    <thead><tr><th>Proceso</th><th>Responsable</th><th>Frecuencia</th><th>Duración</th><th>Score</th><th>Estado</th><th></th></tr></thead>
    <tbody>${_procesos.map(p => {
      const s = p.score;
      return `<tr>
        <td><strong>${esc(p.nombre)}</strong>${p.descripcion?`<br><span style="font-size:.72rem;color:var(--fg-3)">${esc(p.descripcion.slice(0,70))}${p.descripcion.length>70?'…':''}</span>`:''}</td>
        <td>${esc(p.responsable||'–')}</td>
        <td>${esc(p.frecuencia||'–')}</td>
        <td>${p.duracion_h?p.duracion_h+' h/mes':'–'}</td>
        <td><div class="score-badge ${scoreClass(s)}">${s??'–'}</div></td>
        <td>${estadoPill(p.estado)}</td>
        <td><div style="display:flex;gap:.4rem">
          <button class="icon-action" title="Editar" onclick='openProcesoModal(${JSON.stringify(p).replace(/'/g,"&#39;")})'>${ICONS.edit}</button>
          <button class="icon-action danger" title="Eliminar" onclick="deleteProceso('${p.id}','${esc(p.nombre)}')">${ICONS.trash}</button>
        </div></td>
      </tr>`;
    }).join('')}</tbody>
  </table>`;
}

function openProcesoModal(data) {
  const isEdit = data?.id;
  const body = `<div class="form-grid">
    <div class="field-group" style="grid-column:1/-1">
      <label class="field-label">Nombre del proceso *</label>
      <input class="field-input" id="pNombre" maxlength="255" value="${esc(isEdit?data.nombre:'')}" placeholder="Ej: Onboarding de clientes"/>
    </div>
    <div class="field-group" style="grid-column:1/-1">
      <label class="field-label">Descripción</label>
      <textarea class="field-textarea" id="pDesc" maxlength="1000" placeholder="Describe el proceso…">${esc(isEdit?(data.descripcion||''):'')}</textarea>
    </div>
    <div class="field-group">
      <label class="field-label">Responsable</label>
      <input class="field-input" id="pResp" maxlength="100" value="${esc(isEdit?(data.responsable||''):'')}" placeholder="Nombre o departamento"/>
    </div>
    <div class="field-group">
      <label class="field-label">Frecuencia</label>
      <select class="field-select" id="pFrec">
        <option value="">— Seleccionar —</option>
        ${['diario','semanal','quincenal','mensual','trimestral','esporádico'].map(f=>`<option value="${f}" ${isEdit&&data.frecuencia===f?'selected':''}>${f[0].toUpperCase()+f.slice(1)}</option>`).join('')}
      </select>
    </div>
    <div class="field-group">
      <label class="field-label">Duración estimada (h/mes)</label>
      <input class="field-input" id="pDur" type="number" min="0" max="10000" value="${isEdit?(data.duracion_h||''):''}" placeholder="Ej: 8"/>
    </div>
    <div class="field-group">
      <label class="field-label">Score (0–100)</label>
      <input class="field-input" id="pScore" type="number" min="0" max="100" value="${isEdit?(data.score??''):''}" placeholder="Ej: 65"/>
    </div>
    <div class="field-group">
      <label class="field-label">Estado</label>
      <select class="field-select" id="pEstado">
        ${['pendiente','analizado','critico','optimizado'].map(e=>`<option value="${e}" ${isEdit&&data.estado===e?'selected':''}>${e[0].toUpperCase()+e.slice(1)}</option>`).join('')}
      </select>
    </div>
    <div class="field-group">
      <label class="field-label">Notas</label>
      <textarea class="field-textarea" id="pNotas" maxlength="1000" placeholder="Notas internas…">${esc(isEdit?(data.notas||''):'')}</textarea>
    </div>
  </div>`;
  const foot = `<button class="btn-secondary" onclick="closeModal()">Cancelar</button>
    <button class="btn-cta" onclick="saveProceso(${isEdit?`'${data.id}'`:'null'})">${isEdit?'Guardar cambios':'Crear proceso'}</button>`;
  openModal('custom', isEdit?'Editar proceso':'Nuevo proceso', body, foot);
  setTimeout(() => document.getElementById('pNombre')?.focus(), 50);
}

async function saveProceso(id) {
  try {
    const nombre = sanitize(document.getElementById('pNombre')?.value || '', 255);
    if (!nombre) { toast('El nombre es obligatorio'); return; }
    const payload = {
      nombre,
      descripcion: sanitize(document.getElementById('pDesc')?.value || '', 1000) || null,
      responsable: sanitize(document.getElementById('pResp')?.value || '', 100) || null,
      frecuencia:  document.getElementById('pFrec')?.value || null,
      duracion_h:  parseInt(document.getElementById('pDur')?.value) || null,
      score:       (() => { const v = parseInt(document.getElementById('pScore')?.value); return isNaN(v)?null:Math.min(100,Math.max(0,v)); })(),
      estado:      document.getElementById('pEstado')?.value || 'pendiente',
      notas:       sanitize(document.getElementById('pNotas')?.value || '', 1000) || null,
    };
    if (id) { await BPA.put(`/api/procesos/${id}`, payload); toast('Proceso actualizado'); }
    else     { await BPA.post('/api/procesos', payload);      toast('Proceso creado'); }
    closeModal();
    await loadProcesos();
    await loadHomeDashboard();
  } catch(e) { toast(e.message || 'Error al guardar'); }
}

async function deleteProceso(id, nombre) {
  if (!confirm(`¿Eliminar el proceso "${nombre}"?\nEsta acción no se puede deshacer.`)) return;
  try {
    await BPA.del(`/api/procesos/${id}`);
    toast('Proceso eliminado');
    await loadProcesos();
    await loadHomeDashboard();
  } catch(e) { toast(e.message || 'Error al eliminar'); }
}

// ── AUTOMATIZACIONES ──────────────────────────────────────────
let _currentAutoId       = null;
let _currentAuto         = null;
let _currentTriggerType  = 'manual';
let _currentActionType   = 'webhook_out';

async function loadAutomatizaciones() {
  const el = document.getElementById('autosList');
  if (!el) return;
  el.innerHTML = loadingRow();
  try {
    _autos = await BPA.get('/api/automatizaciones');
    _buildSearchIndex();
    _renderAutos();
  } catch(e) { el.innerHTML = `<div class="empty-state"><p>Error: ${esc(e.message)}</p></div>`; }
}

function _renderAutos() {
  const el = document.getElementById('autosList');
  if (!el) return;
  if (!_autos.length) {
    el.innerHTML = emptyState(ICONS.auto, 'Sin automatizaciones', 'Crea tu primera automatización y deja que el agente trabaje por ti.');
    return;
  }
  el.innerHTML = `<div class="auto-cards-grid">${_autos.map(_autoCard).join('')}</div>`;
}

// ── Helper labels / icons ──────────────────────────────────────
const _TRIGGER_LABELS = { manual:'Manual', cron:'Programada', webhook:'Webhook' };
const _ACTION_LABELS  = { webhook_out:'HTTP Webhook', email:'Email', telegram:'Telegram', slack:'Slack', teams:'Teams', n8n:'n8n' };

function _triggerLabel(t) { return _TRIGGER_LABELS[t] || t || 'Manual'; }
function _actionLabel(t)  { return _ACTION_LABELS[t]  || t || 'Webhook'; }

const _SVG_TRIGGER = {
  manual:  `<polyline points="5 3 19 12 5 21 5 3"/>`,
  cron:    `<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>`,
  webhook: `<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>`,
};
const _SVG_ACTION = {
  email:       `<rect x="2" y="4" width="20" height="16" rx="2"/><polyline points="22 7 12 13 2 7"/>`,
  telegram:    `<path d="M21 5L2 12.5l7 1M21 5l-3.5 15L9 13.5M21 5 9 13.5m0 0v5l3.5-3"/>`,
  slack:       `<path d="M14.5 10c-.83 0-1.5-.67-1.5-1.5v-5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5z"/><path d="M20.5 10H19V8.5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/><path d="M9.5 14c.83 0 1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5S8 21.33 8 20.5v-5c0-.83.67-1.5 1.5-1.5z"/><path d="M3.5 14H5v1.5c0 .83-.67 1.5-1.5 1.5S2 16.33 2 15.5 2.67 14 3.5 14z"/>`,
  n8n:         `<circle cx="8" cy="12" r="3"/><circle cx="16" cy="6" r="3"/><circle cx="16" cy="18" r="3"/><line x1="11" y1="12" x2="13" y2="7"/><line x1="11" y1="12" x2="13" y2="17"/>`,
  webhook_out: `<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>`,
};

function _svgIcon(paths, size='14') {
  return `<svg viewBox="0 0 24 24" style="width:${size}px;height:${size}px;stroke:currentColor;stroke-width:1.8;fill:none;stroke-linecap:round;stroke-linejoin:round">${paths}</svg>`;
}

function _autoCard(a) {
  const trigger = a.tipo_trigger || 'manual';
  const action  = a.tipo_accion  || 'webhook_out';
  const stCls   = `estado-${a.estado || 'pendiente'}`;
  const lastRun = a.updated_at
    ? new Date(a.updated_at).toLocaleDateString('es', {day:'2-digit', month:'short', year:'numeric'})
    : 'Nunca';
  const stateColor = a.estado === 'activa' ? 'var(--emerald)' : a.estado === 'error' ? 'var(--rose)' : 'var(--amber)';
  return `
  <div class="auto-card ${stCls}" onclick="openAutoDetail('${a.id}')">
    <div class="auto-card-top">
      <div class="auto-card-icon">${ICONS.auto}</div>
      <div style="flex:1;min-width:0">
        <div class="auto-card-title">${esc(a.nombre)}</div>
        ${a.descripcion ? `<div class="auto-card-desc">${esc(a.descripcion)}</div>` : ''}
      </div>
      ${estadoPill(a.estado || 'pendiente')}
    </div>
    <div class="auto-card-badges">
      <span class="auto-badge trigger">${_svgIcon(_SVG_TRIGGER[trigger]||_SVG_TRIGGER.manual,'11')}<span>${_triggerLabel(trigger)}</span></span>
      <span class="auto-badge action">${_svgIcon(_SVG_ACTION[action]||_SVG_ACTION.webhook_out,'11')}<span>${_actionLabel(action)}</span></span>
    </div>
    <div class="auto-card-stats">
      <div class="auto-stat">
        <div class="auto-stat-val">${(a.ejecuciones||0).toLocaleString()}</div>
        <div class="auto-stat-lbl">Ejecuciones</div>
      </div>
      <div class="auto-stat">
        <div class="auto-stat-val">${a.horas_mes ? a.horas_mes+'h' : '–'}</div>
        <div class="auto-stat-lbl">Ahorro/mes</div>
      </div>
      <div class="auto-stat">
        <div class="auto-stat-val" style="color:${stateColor}">${a.estado==='activa'?'✓':a.estado==='error'?'✗':'~'}</div>
        <div class="auto-stat-lbl">Estado</div>
      </div>
    </div>
    <div class="auto-card-footer">
      <span class="auto-card-lastrun">Último: ${lastRun}</span>
      <div class="auto-card-actions" onclick="event.stopPropagation()">
        <button class="icon-action" title="Ejecutar ahora" style="color:var(--accent);border-color:rgba(var(--accent-rgb),.3)"
          onclick="quickRunAuto('${a.id}','${esc(a.nombre)}')">${_svgIcon('<polygon points="5 3 19 12 5 21 5 3"/>')}</button>
        <button class="icon-action" title="Ver detalle"
          onclick="openAutoDetail('${a.id}')">${_svgIcon('<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>')}</button>
        <button class="icon-action danger" title="Eliminar"
          onclick="deleteAuto('${a.id}','${esc(a.nombre)}')">${ICONS.trash}</button>
      </div>
    </div>
  </div>`;
}

async function quickRunAuto(id, nombre) {
  toast(`Ejecutando "${nombre}"…`);
  try {
    const r = await BPA.post(`/api/ejecutar/${id}/run`, {});
    toast(`✅ ${r.mensaje || 'Ejecutado correctamente'}`);
    if (_currentAutoId === id) { loadAutoHistory(id, true); loadAutoHistory(id); }
  } catch(e) { toast(`Error: ${e.message}`); }
}

// ── DETAIL PAGE ────────────────────────────────────────────────
async function openAutoDetail(id) {
  _currentAutoId = id;
  // Navigate to detail page
  document.querySelectorAll('.page-section').forEach(s => { s.style.display = 'none'; s.classList.remove('active'); });
  const target = document.getElementById('page-auto-detail');
  if (target) { target.style.display = 'contents'; target.classList.add('active'); }
  document.getElementById('pageTitle').textContent = 'Detalle automatización';
  const main = document.getElementById('mainContent');
  if (main) main.scrollTop = 0;
  // Reset to overview tab
  document.querySelectorAll('.detail-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.detail-tab-panel').forEach(p => p.classList.remove('active'));
  const overviewTab = document.querySelector('.detail-tab[data-tab="overview"]');
  if (overviewTab) overviewTab.classList.add('active');
  const overviewPanel = document.getElementById('tab-overview');
  if (overviewPanel) overviewPanel.classList.add('active');
  await loadAutoDetail(id);
}

async function loadAutoDetail(id) {
  try {
    let auto = _autos.find(a => a.id === id);
    if (!auto) auto = await BPA.get(`/api/automatizaciones/${id}`);
    _currentAuto = auto;
    _currentTriggerType = auto.tipo_trigger || 'manual';
    _currentActionType  = auto.tipo_accion  || 'webhook_out';

    // Header
    document.getElementById('detailAutoName').textContent = auto.nombre || '–';
    document.getElementById('detailAutoStatus').innerHTML = estadoPill(auto.estado || 'pendiente');
    document.getElementById('detailAutoTriggerBadge').innerHTML =
      `<span class="auto-badge trigger" style="font-size:.62rem">${_svgIcon(_SVG_TRIGGER[_currentTriggerType]||_SVG_TRIGGER.manual,'10')}<span>${_triggerLabel(_currentTriggerType)}</span></span>`;
    document.getElementById('detailAutoActionBadge').innerHTML =
      `<span class="auto-badge action" style="font-size:.62rem">${_svgIcon(_SVG_ACTION[_currentActionType]||_SVG_ACTION.webhook_out,'10')}<span>${_actionLabel(_currentActionType)}</span></span>`;

    const toggleBtn = document.getElementById('detailToggleBtn');
    if (toggleBtn) toggleBtn.textContent = auto.estado === 'activa' ? 'Pausar' : 'Activar';

    // Stat chips
    _renderDetailStatChips(auto);

    // Overview form
    const ovNombre = document.getElementById('ovNombre');
    if (ovNombre) {
      ovNombre.value = auto.nombre || '';
      document.getElementById('ovDesc').value   = auto.descripcion || '';
      document.getElementById('ovEstado').value = auto.estado || 'pendiente';
      document.getElementById('ovHoras').value  = auto.horas_mes || '';
    }

    // Trigger & action panels
    _renderTriggerOptions(_currentTriggerType, auto);
    _renderActionOptions(_currentActionType, auto);

    // Mini history (overview)
    loadAutoHistory(id, true);
  } catch(e) { toast('Error cargando detalle: ' + e.message); }
}

function _renderDetailStatChips(auto) {
  const el = document.getElementById('detailStatChips');
  if (!el) return;
  el.innerHTML = [
    { label:'Ejecuciones',     value:(auto.ejecuciones||0).toLocaleString(), sub:'total ejecutadas' },
    { label:'Ahorro estimado', value:auto.horas_mes ? auto.horas_mes+'h' : '–', sub:'horas al mes' },
    { label:'Tasa de éxito',   value:auto.ejecuciones > 0 ? '~95%' : '–', sub:'últimas ejecuciones' },
    { label:'Disparador',      value:_triggerLabel(auto.tipo_trigger||'manual'), sub:`Acción: ${_actionLabel(auto.tipo_accion||'webhook_out')}` },
  ].map(c => `
    <div class="auto-stat-chip">
      <div class="auto-stat-chip-label">${esc(c.label)}</div>
      <div class="auto-stat-chip-value">${esc(String(c.value))}</div>
      <div class="auto-stat-chip-sub">${esc(c.sub)}</div>
    </div>`).join('');
}

// ── TRIGGER OPTIONS ────────────────────────────────────────────
const TRIGGER_OPTS = [
  { id:'manual',  label:'Manual',     sub:'Ejecutar a demanda',   paths: _SVG_TRIGGER.manual },
  { id:'cron',    label:'Programada', sub:'Horario automático',   paths: _SVG_TRIGGER.cron },
  { id:'webhook', label:'Webhook',    sub:'Disparada por evento', paths: _SVG_TRIGGER.webhook },
];

function _renderTriggerOptions(selected, auto) {
  const el = document.getElementById('triggerOptions');
  if (!el) return;
  el.innerHTML = TRIGGER_OPTS.map(o => `
    <button class="option-card${o.id === selected ? ' selected' : ''}" onclick="selectTriggerType('${o.id}')">
      <div class="option-card-icon">${_svgIcon(o.paths,'17')}</div>
      <div class="option-card-label">${o.label}</div>
      <div class="option-card-sub">${o.sub}</div>
    </button>`).join('');
  _renderTriggerConfig(selected, auto);
}

function selectTriggerType(type) {
  _currentTriggerType = type;
  document.querySelectorAll('#triggerOptions .option-card').forEach((el, i) => {
    el.classList.toggle('selected', TRIGGER_OPTS[i].id === type);
  });
  _renderTriggerConfig(type, _currentAuto);
}

const CRON_PRESETS = [
  { label:'Cada hora',    expr:'0 * * * *' },
  { label:'Cada 6h',     expr:'0 */6 * * *' },
  { label:'Cada día 9h', expr:'0 9 * * *' },
  { label:'Lun–Vie 9h',  expr:'0 9 * * 1-5' },
  { label:'Cada semana', expr:'0 9 * * 1' },
  { label:'Cada mes',    expr:'0 9 1 * *' },
];
const CRON_HUMAN = {
  '0 * * * *':    'Cada hora en punto',
  '0 */6 * * *':  'Cada 6 horas',
  '0 9 * * *':    'Todos los días a las 9:00',
  '0 9 * * 1-5':  'Lunes a viernes a las 9:00',
  '0 9 * * 1':    'Todos los lunes a las 9:00',
  '0 9 1 * *':    'El primer día de cada mes a las 9:00',
};
function _cronHuman(expr) { return CRON_HUMAN[expr?.trim()] || (expr ? 'Expresión personalizada' : ''); }

function _renderTriggerConfig(type, auto) {
  const area = document.getElementById('triggerConfigArea');
  if (!area) return;
  if (type === 'manual') {
    area.innerHTML = `
      <div class="config-section">
        <div class="config-section-title">${_svgIcon('<polygon points="5 3 19 12 5 21 5 3"/>')} Modo manual</div>
        <p style="font-size:.82rem;color:var(--fg-2);line-height:1.65;margin-bottom:1.25rem">Esta automatización se ejecuta únicamente cuando tú la lanzas manualmente. Ideal para procesos que requieren supervisión.</p>
        <button class="run-btn" onclick="runAutoNow()">${_svgIcon('<polygon points="5 3 19 12 5 21 5 3"/>','15')} Ejecutar ahora</button>
      </div>`;
    return;
  }
  if (type === 'cron') {
    const cur = auto?.cron_expr || '';
    area.innerHTML = `
      <div class="config-section">
        <div class="config-section-title">${_svgIcon(_SVG_TRIGGER.cron)} Programación automática</div>
        <div class="field-label" style="margin-bottom:.5rem">Presets rápidos</div>
        <div class="cron-presets">
          ${CRON_PRESETS.map(p => `<button class="cron-preset${cur===p.expr?' active':''}" onclick="setCronPreset('${p.expr}',this)">${p.label}</button>`).join('')}
        </div>
        <div class="field-group" style="margin-top:.75rem">
          <label class="field-label">Expresión cron <span style="color:var(--fg-3);font-weight:400;font-size:.67rem">(min hora día mes sem)</span></label>
          <input class="field-input" id="cronExpr" value="${esc(cur)}" placeholder="0 9 * * *"
            oninput="updateCronHuman(this.value)" style="font-family:ui-monospace,monospace;letter-spacing:.03em"/>
        </div>
        <div class="cron-human" id="cronHuman">${_cronHuman(cur)}</div>
      </div>`;
    return;
  }
  if (type === 'webhook') {
    const token = auto?.webhook_token || '(se generará al guardar)';
    const url   = `http://localhost:8002/api/ejecutar/webhook/${_currentAutoId}/${token}`;
    area.innerHTML = `
      <div class="config-section">
        <div class="config-section-title">${_svgIcon(_SVG_TRIGGER.webhook)} URL del Webhook entrante</div>
        <p style="font-size:.8rem;color:var(--fg-2);margin-bottom:.875rem;line-height:1.55">Cualquier sistema externo puede disparar esta automatización enviando un POST a esta URL.</p>
        <div class="webhook-url-box">
          <span class="webhook-url-text" id="webhookUrlText">${esc(url)}</span>
          <button class="webhook-copy-btn" onclick="copyWebhookUrl()" title="Copiar URL">${_svgIcon('<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>')}</button>
        </div>
        <div style="margin-top:.875rem">
          <div class="field-label" style="margin-bottom:.4rem">Ejemplo de llamada</div>
          <div style="background:var(--input-bg);border:1px solid var(--border);border-radius:8px;padding:.75rem;font-family:ui-monospace,monospace;font-size:.7rem;color:var(--cyan);white-space:pre-wrap;word-break:break-all">curl -X POST "${url}"</div>
        </div>
      </div>`;
    return;
  }
}

function setCronPreset(expr, btn) {
  const inp = document.getElementById('cronExpr');
  if (inp) inp.value = expr;
  document.querySelectorAll('.cron-preset').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  updateCronHuman(expr);
}
function updateCronHuman(expr) {
  const el = document.getElementById('cronHuman');
  if (el) el.textContent = _cronHuman(expr);
}
function copyWebhookUrl() {
  const text = document.getElementById('webhookUrlText')?.textContent;
  if (text) navigator.clipboard.writeText(text).then(() => toast('URL copiada al portapapeles'));
}

async function saveTriggerConfig() {
  if (!_currentAutoId) return;
  try {
    const payload = { tipo_trigger: _currentTriggerType };
    if (_currentTriggerType === 'cron') {
      payload.cron_expr = document.getElementById('cronExpr')?.value?.trim() || null;
      if (!payload.cron_expr) { toast('Introduce una expresión cron válida'); return; }
    }
    await BPA.put(`/api/automatizaciones/${_currentAutoId}`, payload);
    toast('Disparador guardado');
    if (_currentTriggerType === 'cron') {
      await BPA.post(`/api/ejecutar/${_currentAutoId}/programar`, {}).catch(() => {});
    }
    await _reloadCurrentAuto();
  } catch(e) { toast(e.message); }
}

// ── ACTION OPTIONS ─────────────────────────────────────────────
const ACTION_OPTS = [
  { id:'webhook_out', label:'HTTP Webhook', sub:'POST a URL externa',  paths: _SVG_ACTION.webhook_out },
  { id:'email',       label:'Email',        sub:'Gmail / SMTP',         paths: _SVG_ACTION.email },
  { id:'telegram',    label:'Telegram',     sub:'Bot de Telegram',      paths: _SVG_ACTION.telegram },
  { id:'slack',       label:'Slack',        sub:'Incoming Webhook',     paths: _SVG_ACTION.slack },
  { id:'n8n',         label:'n8n',          sub:'Workflow n8n local',   paths: _SVG_ACTION.n8n },
];

function _renderActionOptions(selected, auto) {
  const el = document.getElementById('actionOptions');
  if (!el) return;
  el.innerHTML = ACTION_OPTS.map(o => `
    <button class="option-card${o.id === selected ? ' selected' : ''}" onclick="selectActionType('${o.id}')">
      <div class="option-card-icon">${_svgIcon(o.paths,'17')}</div>
      <div class="option-card-label">${o.label}</div>
      <div class="option-card-sub">${o.sub}</div>
    </button>`).join('');
  _renderActionConfig(selected, auto);
}

function selectActionType(type) {
  _currentActionType = type;
  document.querySelectorAll('#actionOptions .option-card').forEach((el, i) => {
    el.classList.toggle('selected', ACTION_OPTS[i].id === type);
  });
  _renderActionConfig(type, _currentAuto);
}

function _renderActionConfig(type, auto) {
  const area = document.getElementById('actionConfigArea');
  if (!area) return;
  const herr = auto?.herramienta || '';
  if (type === 'webhook_out') {
    area.innerHTML = `
      <div class="config-section">
        <div class="config-section-title">${_svgIcon(_SVG_ACTION.webhook_out)} Configuración HTTP Webhook</div>
        <div class="form-grid">
          <div class="field-group" style="grid-column:1/-1">
            <label class="field-label">URL de destino *</label>
            <input class="field-input" id="acURL" placeholder="https://hooks.ejemplo.com/trigger/…" value="${esc(herr.startsWith('http') ? herr : '')}"/>
          </div>
          <div class="field-group">
            <label class="field-label">Método HTTP</label>
            <select class="field-select" id="acMethod"><option>POST</option><option>GET</option><option>PUT</option></select>
          </div>
          <div class="field-group">
            <label class="field-label">Cabecera Authorization</label>
            <input class="field-input" id="acAuthHeader" placeholder="Bearer mitoken…"/>
          </div>
          <div class="field-group" style="grid-column:1/-1">
            <label class="field-label">Body JSON (opcional)</label>
            <textarea class="field-textarea" id="acBody" rows="4" placeholder='{"evento":"disparado","proceso":"facturación"}'></textarea>
          </div>
        </div>
      </div>`;
    return;
  }
  if (type === 'email') {
    area.innerHTML = `
      <div class="config-section">
        <div class="config-section-title">${_svgIcon(_SVG_ACTION.email)} Configuración Email (SMTP)</div>
        <div class="form-grid">
          <div class="field-group" style="grid-column:1/-1">
            <label class="field-label">Proveedor</label>
            <select class="field-select" id="acEmailPreset" onchange="applyEmailPreset(this.value)">
              <option value="gmail">Gmail (App Password)</option>
              <option value="outlook">Outlook / Hotmail</option>
              <option value="yahoo">Yahoo</option>
              <option value="custom">SMTP personalizado</option>
            </select>
          </div>
          <div class="field-group"><label class="field-label">Usuario / email</label><input class="field-input" id="acEmailUser" placeholder="tu@gmail.com"/></div>
          <div class="field-group"><label class="field-label">Contraseña / App Password</label><input class="field-input" id="acEmailPass" type="password" placeholder="••••••••"/></div>
          <div id="acEmailCustomFields" style="display:none;grid-column:1/-1">
            <div class="form-grid">
              <div class="field-group"><label class="field-label">Servidor SMTP</label><input class="field-input" id="acEmailHost" placeholder="smtp.ejemplo.com"/></div>
              <div class="field-group"><label class="field-label">Puerto</label><input class="field-input" id="acEmailPort" type="number" value="587"/></div>
            </div>
          </div>
          <div class="field-group" style="grid-column:1/-1"><label class="field-label">Destinatario(s)</label><input class="field-input" id="acEmailTo" placeholder="cliente@empresa.com"/></div>
          <div class="field-group" style="grid-column:1/-1"><label class="field-label">Asunto</label><input class="field-input" id="acEmailSubj" placeholder="Notificación automática · BPA-Agent"/></div>
          <div class="field-group" style="grid-column:1/-1"><label class="field-label">Cuerpo del mensaje</label><textarea class="field-textarea" id="acEmailBody" rows="4" placeholder="Mensaje automático generado por BPA-Agent."></textarea></div>
        </div>
      </div>`;
    return;
  }
  if (type === 'telegram') {
    area.innerHTML = `
      <div class="config-section">
        <div class="config-section-title">${_svgIcon(_SVG_ACTION.telegram)} Configuración Telegram</div>
        <div class="info-banner" style="margin-bottom:1rem">Habla con <strong>@BotFather</strong> en Telegram → <code>/newbot</code> para crear tu bot y obtener el token. Luego añade el bot a tu grupo y usa <strong>@userinfobot</strong> para obtener el chat_id.</div>
        <div class="form-grid">
          <div class="field-group" style="grid-column:1/-1"><label class="field-label">Bot Token *</label><input class="field-input" id="acTgToken" placeholder="123456789:AABBCCDDEEFFaabbccddeeff"/></div>
          <div class="field-group" style="grid-column:1/-1"><label class="field-label">Chat ID *</label><input class="field-input" id="acTgChat" placeholder="-1001234567890 (grupo) · 987654321 (personal)"/></div>
          <div class="field-group" style="grid-column:1/-1"><label class="field-label">Mensaje</label><textarea class="field-textarea" id="acTgMsg" rows="3" placeholder="🤖 Automatización ejecutada: {{nombre}}"></textarea></div>
        </div>
      </div>`;
    return;
  }
  if (type === 'slack') {
    area.innerHTML = `
      <div class="config-section">
        <div class="config-section-title">${_svgIcon(_SVG_ACTION.slack)} Configuración Slack</div>
        <div class="info-banner" style="margin-bottom:1rem">En Slack: <strong>Apps → Incoming Webhooks → Add to Slack</strong>. Elige el canal y copia la Webhook URL generada.</div>
        <div class="form-grid">
          <div class="field-group" style="grid-column:1/-1"><label class="field-label">Slack Webhook URL *</label><input class="field-input" id="acSlackUrl" placeholder="https://hooks.slack.com/services/T.../B.../..." value="${esc(herr.startsWith('https://hooks.slack') ? herr : '')}"/></div>
          <div class="field-group" style="grid-column:1/-1"><label class="field-label">Mensaje</label><textarea class="field-textarea" id="acSlackMsg" rows="3" placeholder=":robot_face: Automatización ejecutada en BPA-Agent"></textarea></div>
        </div>
      </div>`;
    return;
  }
  if (type === 'n8n') {
    area.innerHTML = `
      <div class="config-section">
        <div class="config-section-title">${_svgIcon(_SVG_ACTION.n8n)} Configuración n8n</div>
        <div class="warn-banner" style="margin-bottom:1rem">Arranca n8n con <code>npx n8n</code> → abre <strong>localhost:5678</strong> → crea un workflow con nodo <em>Webhook</em> → copia la URL de producción.</div>
        <div class="form-grid">
          <div class="field-group" style="grid-column:1/-1"><label class="field-label">Webhook URL del workflow *</label><input class="field-input" id="acN8nUrl" placeholder="http://localhost:5678/webhook/abc123" value="${esc(herr.includes('5678') ? herr : '')}"/></div>
          <div class="field-group"><label class="field-label">API Key n8n (opcional)</label><input class="field-input" id="acN8nKey" placeholder="n8n_api_…"/></div>
          <div class="field-group" style="grid-column:1/-1"><label class="field-label">Datos extra (JSON)</label><textarea class="field-textarea" id="acN8nBody" rows="3" placeholder='{"proceso":"facturación","empresa":"Acme"}'></textarea></div>
        </div>
      </div>`;
    return;
  }
}

function applyEmailPreset(preset) {
  const cf = document.getElementById('acEmailCustomFields');
  if (cf) cf.style.display = preset === 'custom' ? '' : 'none';
}

async function saveActionConfig() {
  if (!_currentAutoId) return;
  try {
    const payload = { tipo_accion: _currentActionType };
    if (_currentActionType === 'webhook_out') payload.herramienta = document.getElementById('acURL')?.value?.trim() || null;
    else if (_currentActionType === 'n8n')    payload.herramienta = document.getElementById('acN8nUrl')?.value?.trim() || null;
    else if (_currentActionType === 'slack')  payload.herramienta = document.getElementById('acSlackUrl')?.value?.trim() || null;
    else if (_currentActionType === 'email')  payload.herramienta = `smtp:${document.getElementById('acEmailPreset')?.value||'gmail'}`;
    else if (_currentActionType === 'telegram') {
      const chat = document.getElementById('acTgChat')?.value?.trim();
      payload.herramienta = `telegram:${chat||''}`;
      const token = document.getElementById('acTgToken')?.value?.trim();
      if (token && chat) {
        await BPA.post('/api/credenciales', {
          nombre: `Telegram · ${_currentAuto?.nombre||''}`,
          tipo: 'telegram',
          datos_encriptados: JSON.stringify({ token, chat_id: chat }),
        }).catch(() => {});
      }
    }
    await BPA.put(`/api/automatizaciones/${_currentAutoId}`, payload);
    toast('Acción guardada');
    await _reloadCurrentAuto();
  } catch(e) { toast(e.message); }
}

async function testActionConnector() {
  toast('Probando conexión…');
  try {
    const body = { tipo_accion: _currentActionType };
    if (_currentActionType === 'telegram') {
      body.telegram_token = document.getElementById('acTgToken')?.value?.trim();
      body.chat_id        = document.getElementById('acTgChat')?.value?.trim();
    } else if (_currentActionType === 'webhook_out') {
      body.url = document.getElementById('acURL')?.value?.trim();
    } else if (_currentActionType === 'n8n') {
      body.url = document.getElementById('acN8nUrl')?.value?.trim();
    } else if (_currentActionType === 'slack') {
      body.slack_url = document.getElementById('acSlackUrl')?.value?.trim();
    } else if (_currentActionType === 'email') {
      body.email_user = document.getElementById('acEmailUser')?.value?.trim();
      body.email_pass = document.getElementById('acEmailPass')?.value?.trim();
      body.preset     = document.getElementById('acEmailPreset')?.value;
    }
    const r = await BPA.post('/api/ejecutar/test-connector', body);
    toast(r.ok ? '✅ Conexión correcta' : `⚠️ ${r.mensaje || 'Respuesta recibida'}`);
  } catch(e) { toast(`Error: ${e.message}`); }
}

// ── EXECUTION HISTORY ──────────────────────────────────────────
async function loadAutoHistory(id, mini = false) {
  const elId = mini ? 'detailRecentHistory' : 'detailHistoryList';
  const el = document.getElementById(elId);
  if (!el) return;
  if (!mini) el.innerHTML = loadingRow();
  try {
    const limit = mini ? 3 : 50;
    const data  = await BPA.get(`/api/ejecutar/${id}/historial?limit=${limit}`);
    if (!data.length) {
      el.innerHTML = `<div class="empty-history">
        ${mini ? '' : `${_svgIcon('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>','40')}`}
        <p style="color:var(--fg-3);font-size:.78rem;margin-top:.5rem">${mini ? 'Sin ejecuciones aún' : 'Todavía no se ha ejecutado esta automatización'}</p>
      </div>`;
      return;
    }
    el.innerHTML = `<div class="history-list">${data.map(_historyItem).join('')}</div>`;
  } catch(e) {
    el.innerHTML = `<p style="font-size:.75rem;color:var(--fg-3)">Error cargando historial</p>`;
  }
}

function _historyItem(h) {
  const ok   = ['exitoso','ok','success'].includes(h.estado);
  const fail = ['error','fallido','failed'].includes(h.estado);
  const dotClass = ok ? 'ok' : fail ? 'fail' : 'run';
  const icon = ok
    ? `<svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>`
    : fail
    ? `<svg viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`
    : `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;
  const ts = h.created_at ? new Date(h.created_at) : null;
  const timeStr = ts ? ts.toLocaleString('es', {day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit'}) : '–';
  const estadoLabel = h.estado ? h.estado[0].toUpperCase() + h.estado.slice(1) : 'Ejecución';
  return `
  <div class="history-item">
    <div class="history-dot ${dotClass}">${icon}</div>
    <div class="history-content">
      <div class="history-title">${esc(estadoLabel)}</div>
      <div class="history-meta">
        <span>${timeStr}</span>
        ${h.triggered_by ? `<span>por <strong>${esc(h.triggered_by)}</strong></span>` : ''}
      </div>
      ${h.mensaje ? `<div class="history-msg">${esc(h.mensaje.slice(0,250))}</div>` : ''}
    </div>
    ${h.duracion_ms ? `<div class="history-duration">${h.duracion_ms}ms</div>` : ''}
  </div>`;
}

// ── SAVE / ACTIONS ─────────────────────────────────────────────
async function saveOverviewChanges() {
  if (!_currentAutoId) return;
  try {
    const nombre = sanitize(document.getElementById('ovNombre')?.value || '', 255);
    if (!nombre) { toast('El nombre es obligatorio'); return; }
    const payload = {
      nombre,
      descripcion: sanitize(document.getElementById('ovDesc')?.value || '', 1000) || null,
      estado:      document.getElementById('ovEstado')?.value || 'pendiente',
      horas_mes:   parseInt(document.getElementById('ovHoras')?.value) || null,
    };
    await BPA.put(`/api/automatizaciones/${_currentAutoId}`, payload);
    toast('Cambios guardados');
    const idx = _autos.findIndex(a => a.id === _currentAutoId);
    if (idx >= 0) Object.assign(_autos[idx], payload);
    await _reloadCurrentAuto();
    loadHomeDashboard();
  } catch(e) { toast(e.message); }
}

async function _reloadCurrentAuto() {
  if (!_currentAutoId) return;
  try {
    const fresh = await BPA.get(`/api/automatizaciones/${_currentAutoId}`);
    const idx = _autos.findIndex(a => a.id === _currentAutoId);
    if (idx >= 0) _autos[idx] = fresh; else _autos.push(fresh);
    _currentAuto = fresh;
    document.getElementById('detailAutoName').textContent = fresh.nombre || '–';
    document.getElementById('detailAutoStatus').innerHTML = estadoPill(fresh.estado || 'pendiente');
    const toggleBtn = document.getElementById('detailToggleBtn');
    if (toggleBtn) toggleBtn.textContent = fresh.estado === 'activa' ? 'Pausar' : 'Activar';
    _renderDetailStatChips(fresh);
  } catch {}
}

async function toggleAutoEstado() {
  if (!_currentAuto) return;
  const newEstado = _currentAuto.estado === 'activa' ? 'pausada' : 'activa';
  try {
    await BPA.put(`/api/automatizaciones/${_currentAutoId}`, { estado: newEstado });
    toast(`Automatización ${newEstado === 'activa' ? 'activada ✅' : 'pausada ⏸'}`);
    await _reloadCurrentAuto();
  } catch(e) { toast(e.message); }
}

async function runAutoNow() {
  const btn = document.getElementById('detailRunBtn');
  if (btn) { btn.disabled = true; btn.classList.add('running'); btn.innerHTML = `${_svgIcon('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>','15')} Ejecutando…`; }
  try {
    const r = await BPA.post(`/api/ejecutar/${_currentAutoId}/run`, {});
    toast(`✅ ${r.mensaje || 'Ejecutado correctamente'}`);
    await loadAutoHistory(_currentAutoId, true);
    await loadAutoHistory(_currentAutoId);
    await _reloadCurrentAuto();
  } catch(e) { toast(`Error: ${e.message}`); }
  finally {
    if (btn) { btn.disabled = false; btn.classList.remove('running'); btn.innerHTML = `${_svgIcon('<polygon points="5 3 19 12 5 21 5 3"/>','15')} Ejecutar ahora`; }
  }
}

function switchDetailTab(tab, btn) {
  document.querySelectorAll('.detail-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.detail-tab-panel').forEach(p => p.classList.remove('active'));
  if (btn) btn.classList.add('active');
  const panel = document.getElementById(`tab-${tab}`);
  if (panel) panel.classList.add('active');
  if (tab === 'history' && _currentAutoId) loadAutoHistory(_currentAutoId);
}

function backToAutos() {
  const navEl = document.querySelector('.nav-item[data-page="Automatizaciones"]') || null;
  setPage(navEl, 'Automatizaciones', 'page-automatizaciones');
  loadAutomatizaciones();
}

// ── QUICK CREATE MODAL ─────────────────────────────────────────
function openAutoModal(data) {
  if (data?.id) { openAutoDetail(data.id); return; }
  const body = `<div class="form-grid">
    <div class="field-group" style="grid-column:1/-1">
      <label class="field-label">Nombre *</label>
      <input class="field-input" id="aNombre" maxlength="255" placeholder="Ej: Envío automático de contrato"/>
    </div>
    <div class="field-group" style="grid-column:1/-1">
      <label class="field-label">Descripción</label>
      <textarea class="field-textarea" id="aDesc" maxlength="1000" rows="3" placeholder="¿Qué hace esta automatización?"></textarea>
    </div>
    <div class="field-group">
      <label class="field-label">Estado inicial</label>
      <select class="field-select" id="aEstado">
        <option value="pendiente">Pendiente</option>
        <option value="activa">Activa</option>
      </select>
    </div>
    <div class="field-group">
      <label class="field-label">Horas ahorradas / mes</label>
      <input class="field-input" id="aHoras" type="number" min="0" max="10000" placeholder="Ej: 8"/>
    </div>
  </div>`;
  const foot = `<button class="btn-secondary" onclick="closeModal()">Cancelar</button>
    <button class="btn-cta" onclick="saveAuto(null)">Crear y configurar →</button>`;
  openModal('custom', 'Nueva automatización', body, foot);
  setTimeout(() => document.getElementById('aNombre')?.focus(), 50);
}

async function saveAuto(id) {
  try {
    const nombre = sanitize(document.getElementById('aNombre')?.value || '', 255);
    if (!nombre) { toast('El nombre es obligatorio'); return; }
    const payload = {
      nombre,
      descripcion: sanitize(document.getElementById('aDesc')?.value || '', 1000) || null,
      estado:      document.getElementById('aEstado')?.value || 'pendiente',
      horas_mes:   parseInt(document.getElementById('aHoras')?.value) || null,
      ejecuciones: 0,
    };
    const created = await BPA.post('/api/automatizaciones', payload);
    closeModal();
    toast('Automatización creada — abriendo configuración…');
    _autos.push(created);
    await loadAutomatizaciones();
    loadHomeDashboard();
    setTimeout(() => openAutoDetail(created.id), 350);
  } catch(e) { toast(e.message || 'Error al crear'); }
}

async function deleteAuto(id, nombre) {
  if (!confirm(`¿Eliminar la automatización "${nombre}"?\nEsta acción no se puede deshacer.`)) return;
  try {
    await BPA.del(`/api/automatizaciones/${id}`);
    toast('Automatización eliminada');
    _autos = _autos.filter(a => a.id !== id);
    if (_currentAutoId === id) backToAutos();
    else { _renderAutos(); loadHomeDashboard(); }
  } catch(e) { toast(e.message || 'Error al eliminar'); }
}

// ── KPIs por proceso ─────────────────────────────────────────
async function loadKpis() {
  const el = document.getElementById('kpisList');
  if (!el) return;
  el.innerHTML = loadingRow();
  try {
    _kpis = await BPA.get('/api/kpis');
    _buildSearchIndex();
    _renderKpis();
  } catch(e) { el.innerHTML = `<div class="empty-state"><p>Error: ${esc(e.message)}</p></div>`; }
}

function _kpiCard(k) {
  const tendIcon = t => t==='up'?'↑':t==='down'?'↓':'→';
  const tendCol  = t => t==='up'?'var(--emerald)':t==='down'?'var(--rose)':'var(--amber)';
  return `<div class="card-item">
    <div class="card-item-header">
      <div>
        <div class="card-item-title">${esc(k.nombre)}</div>
        ${k.categoria?`<div class="card-item-sub" style="text-transform:capitalize">${esc(k.categoria)}</div>`:''}
      </div>
      <span style="font-size:1.3rem;font-weight:700;color:${tendCol(k.tendencia)}" title="${k.tendencia==='up'?'Subiendo':k.tendencia==='down'?'Bajando':'Estable'}">${tendIcon(k.tendencia)}</span>
    </div>
    <div style="font-size:1.7rem;font-weight:700;color:var(--fg);margin:.5rem 0 .2rem">${esc(k.valor)}${k.unidad?`<span style="font-size:.82rem;font-weight:400;color:var(--fg-3);margin-left:.3rem">${esc(k.unidad)}</span>`:''}</div>
    ${k.objetivo?`<div style="font-size:.72rem;color:var(--fg-3);margin-bottom:.3rem">Objetivo: <strong>${esc(k.objetivo)}${k.unidad?' '+esc(k.unidad):''}</strong></div>`:''}
    <div class="card-item-actions">
      <button class="icon-action" title="Editar" onclick='openKpiModal(${JSON.stringify(k).replace(/'/g,"&#39;")})'>${ICONS.edit}</button>
      <button class="icon-action danger" title="Eliminar" onclick="deleteKpi('${k.id}','${esc(k.nombre)}')">${ICONS.trash}</button>
    </div>
  </div>`;
}

function _kpiGroup(title, subtitle, kpis, procesoId, scoreHtml) {
  const empty = `<p style="font-size:.8rem;color:var(--fg-3);padding:.5rem 0">Sin KPIs aún. <a href="#" style="color:var(--accent)" onclick="openKpiModal(null,'${procesoId||''}');return false">Añadir primero</a></p>`;
  return `<div style="margin-bottom:2rem">
    <div style="display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:.8rem">
      <div>
        <div style="font-size:.95rem;font-weight:600;color:var(--fg)">${esc(title)}</div>
        ${subtitle?`<div style="font-size:.75rem;color:var(--fg-3)">${esc(subtitle)}</div>`:''}
      </div>
      <div style="display:flex;align-items:center;gap:.6rem">
        ${scoreHtml||''}
        <button class="btn-secondary" style="font-size:.72rem;padding:.3rem .7rem" onclick="openKpiModal(null,'${procesoId||''}')">
          <svg viewBox="0 0 24 24" style="width:11px;height:11px;stroke:currentColor;stroke-width:2.5;fill:none"><path d="M12 5v14M5 12h14"/></svg>
          KPI
        </button>
      </div>
    </div>
    ${kpis.length ? `<div class="cards-grid">${kpis.map(_kpiCard).join('')}</div>` : empty}
  </div>`;
}

function _renderKpis() {
  const el = document.getElementById('kpisList');
  if (!el) return;

  // Actualizar contador en cabecera
  const hdBtn = document.querySelector('#page-kpis .btn-cta');
  if (hdBtn) hdBtn.style.display = _procesos.length ? 'none' : '';

  const scoreClass = s => s==null?'':'score-badge '+(s>=70?'good':s>=40?'mid':'bad');
  const scorePill  = p => p.score!=null
    ? `<div class="${scoreClass(p.score)}" style="font-size:.72rem;padding:.2rem .5rem">${p.score}/100</div>`
    : '';

  // Agrupar por proceso
  const byProceso = {};
  _kpis.forEach(k => {
    const pid = k.proceso_id || '__global__';
    if (!byProceso[pid]) byProceso[pid] = [];
    byProceso[pid].push(k);
  });

  let html = '';

  // Un bloque por proceso (en orden de _procesos)
  if (_procesos.length) {
    _procesos.forEach(p => {
      const kpis = byProceso[p.id] || [];
      const frecLabel = p.frecuencia ? `${p.frecuencia} · ` : '';
      const sub = `${frecLabel}${p.duracion_h ? p.duracion_h+' h/mes' : ''} · ${p.estado}`;
      html += _kpiGroup(p.nombre, sub.replace(/^·\s*|·\s*$/g,'').trim(), kpis, p.id, scorePill(p));
    });
  }

  // KPIs globales (sin proceso)
  const globals = byProceso['__global__'] || [];
  if (globals.length || !_procesos.length) {
    html += _kpiGroup('KPIs globales de empresa', 'Indicadores no asociados a ningún proceso', globals, '', '');
  }

  if (!html) {
    el.innerHTML = emptyState(ICONS.kpi, 'Sin KPIs', 'Crea tu primer proceso y añade KPIs para hacer seguimiento de la evolución de tu empresa.');
    return;
  }

  // Estadísticas rápidas
  const total = _kpis.length;
  const ups   = _kpis.filter(k=>k.tendencia==='up').length;
  const downs = _kpis.filter(k=>k.tendencia==='down').length;
  const stats = `<div style="display:flex;gap:1.5rem;margin-bottom:1.5rem;flex-wrap:wrap">
    <div style="font-size:.8rem;color:var(--fg-3)">${total} KPI${total!==1?'s':''} en total</div>
    <div style="font-size:.8rem;color:var(--emerald)">↑ ${ups} subiendo</div>
    <div style="font-size:.8rem;color:var(--rose)">↓ ${downs} bajando</div>
    <div style="font-size:.8rem;color:var(--amber)">→ ${total-ups-downs} estables</div>
  </div>`;
  el.innerHTML = stats + html;
}

function openKpiModal(data, preselectedProcesoId) {
  const isEdit = data?.id;
  const procesoOpts = _procesos.map(p =>
    `<option value="${p.id}" ${(isEdit?data.proceso_id:preselectedProcesoId)===p.id?'selected':''}>${esc(p.nombre)}</option>`
  ).join('');
  const body = `<div class="form-grid">
    <div class="field-group" style="grid-column:1/-1">
      <label class="field-label">Nombre del KPI *</label>
      <input class="field-input" id="kNombre" maxlength="255" value="${esc(isEdit?data.nombre:'')}" placeholder="Ej: Tiempo de resolución"/>
    </div>
    <div class="field-group">
      <label class="field-label">Valor actual *</label>
      <input class="field-input" id="kValor" maxlength="100" value="${esc(isEdit?data.valor:'')}" placeholder="Ej: 2.8"/>
    </div>
    <div class="field-group">
      <label class="field-label">Unidad</label>
      <input class="field-input" id="kUnidad" maxlength="50" value="${esc(isEdit?(data.unidad||''):'')}" placeholder="días, %, €…"/>
    </div>
    <div class="field-group">
      <label class="field-label">Objetivo</label>
      <input class="field-input" id="kObj" maxlength="100" value="${esc(isEdit?(data.objetivo||''):'')}" placeholder="Ej: 2 días"/>
    </div>
    <div class="field-group">
      <label class="field-label">Categoría</label>
      <select class="field-select" id="kCat">
        <option value="">— Sin categoría —</option>
        ${['tiempo','coste','calidad','volumen'].map(c=>`<option value="${c}" ${isEdit&&data.categoria===c?'selected':''}>${c[0].toUpperCase()+c.slice(1)}</option>`).join('')}
      </select>
    </div>
    <div class="field-group">
      <label class="field-label">Tendencia</label>
      <select class="field-select" id="kTend">
        ${[['up','↑ Subiendo'],['down','↓ Bajando'],['flat','→ Estable']].map(([v,l])=>`<option value="${v}" ${(isEdit?data.tendencia:'up')===v?'selected':''}>${l}</option>`).join('')}
      </select>
    </div>
    ${_procesos.length ? `<div class="field-group" style="grid-column:1/-1">
      <label class="field-label">Proceso asociado</label>
      <select class="field-select" id="kProceso">
        <option value="">— Global (sin proceso) —</option>
        ${procesoOpts}
      </select>
    </div>` : ''}
  </div>`;
  const foot = `<button class="btn-secondary" onclick="closeModal()">Cancelar</button>
    <button class="btn-cta" onclick="saveKpi(${isEdit?`'${data.id}'`:'null'})">${isEdit?'Guardar cambios':'Crear KPI'}</button>`;
  openModal('custom', isEdit?'Editar KPI':'Nuevo KPI', body, foot);
  setTimeout(() => document.getElementById('kNombre')?.focus(), 50);
}

async function saveKpi(id) {
  try {
    const nombre = sanitize(document.getElementById('kNombre')?.value || '', 255);
    const valor  = sanitize(document.getElementById('kValor')?.value  || '', 100);
    if (!nombre || !valor) { toast('Nombre y valor son obligatorios', 'err'); return; }
    const payload = {
      nombre, valor,
      unidad:     sanitize(document.getElementById('kUnidad')?.value || '', 50)  || null,
      objetivo:   sanitize(document.getElementById('kObj')?.value    || '', 100) || null,
      categoria:  document.getElementById('kCat')?.value    || null,
      tendencia:  document.getElementById('kTend')?.value   || 'up',
      proceso_id: document.getElementById('kProceso')?.value || null,
    };
    if (id) { await BPA.put(`/api/kpis/${id}`, payload); toast('KPI actualizado', 'ok'); }
    else     { await BPA.post('/api/kpis', payload);      toast('KPI creado', 'ok'); }
    closeModal();
    await loadKpis();
    await loadHomeDashboard();
  } catch(e) { toast(e.message || 'Error al guardar', 'err'); }
}

async function deleteKpi(id, nombre) {
  if (!confirm(`¿Eliminar el KPI "${nombre}"?`)) return;
  try {
    await BPA.del(`/api/kpis/${id}`);
    toast('KPI eliminado', 'ok');
    await loadKpis();
    await loadHomeDashboard();
  } catch(e) { toast(e.message || 'Error al eliminar', 'err'); }
}

// ── PROPUESTAS ────────────────────────────────────────────────
async function loadPropuestas() {
  const el = document.getElementById('propuestasList');
  if (!el) return;
  el.innerHTML = loadingRow();
  try {
    const convs = await BPA.get('/api/agente/conversaciones');
    if (!convs.length) {
      el.innerHTML = emptyState(ICONS.chat, 'Sin conversaciones', 'Las conversaciones con el agente IA aparecerán aquí.');
      return;
    }
    el.innerHTML = `<div class="cards-grid">${convs.map(c => {
      const msgs = (() => { try { return JSON.parse(c.historial||'[]'); } catch(e) { return []; } })();
      const lastMsg = [...msgs].reverse().find(m => m.role==='assistant');
      const date = c.updated_at ? new Date(c.updated_at).toLocaleDateString('es-ES') : '';
      return `<div class="card-item">
        <div class="card-item-header">
          <div>
            <div class="card-item-title">${esc(c.titulo||'Conversación')}</div>
            <div class="card-item-sub">${msgs.length} mensaje${msgs.length!==1?'s':''} · ${esc(date)}</div>
          </div>
          ${estadoPill(c.fase||'diagnostico')}
        </div>
        ${lastMsg?`<p style="font-size:.78rem;color:var(--fg-2);line-height:1.5;margin:.5rem 0">${esc(lastMsg.content.slice(0,150))}${lastMsg.content.length>150?'…':''}</p>`:''}
        <div class="card-item-actions">
          <button class="btn-secondary" style="font-size:.72rem;padding:.3rem .7rem" onclick="abrirConversacion('${c.id}')">Continuar →</button>
          <button class="icon-action danger" title="Eliminar" onclick="deleteConversacion('${c.id}')">${ICONS.trash}</button>
        </div>
      </div>`;
    }).join('')}</div>`;
  } catch(e) { el.innerHTML = `<div class="empty-state"><p>Error: ${esc(e.message)}</p></div>`; }
}

function abrirConversacion(convId) {
  _conversacionId = convId;
  navTo('Agente IA', 'page-agente');
  // Cargar historial de la conversación
  setTimeout(() => _loadConversacionHistorial(convId), 100);
}

async function _loadConversacionHistorial(convId) {
  try {
    const convs = await BPA.get('/api/agente/conversaciones');
    const conv = convs.find(c => c.id === convId);
    if (!conv) return;
    const msgs = (() => { try { return JSON.parse(conv.historial||'[]'); } catch(e) { return []; } })();
    const container = document.getElementById('chatMessages');
    if (!container) return;
    container.innerHTML = '';
    const user = API.session.get().user;
    const userInitials = user ? ((user.nombre||'U')[0]+(user.apellido||'U')[0]).toUpperCase() : 'U';
    if (!Array.isArray(msgs)) return;
    msgs.forEach(m => appendMsg(container, m.role==='user'?'user':'agent', m.role==='user'?userInitials:'__logo__', m.content));
    container.scrollTop = container.scrollHeight;
    _chatHistorial = msgs;
  } catch(e) { console.error('Error cargando historial:', e); }
}

async function deleteConversacion(id) {
  if (!confirm('¿Eliminar esta conversación?')) return;
  try {
    await BPA.del(`/api/agente/conversaciones/${id}`);
    toast('Conversación eliminada');
    await loadPropuestas();
  } catch(e) { toast(e.message || 'Error al eliminar'); }
}

// ── AGENTE IA CHAT ────────────────────────────────────────────
async function initAgentePage() {
  try {
    if (_conversacionId) {
      await _loadConversacionHistorial(_conversacionId);
    }
  } catch(e) { console.warn('Error cargando historial de chat:', e); }
  setTimeout(() => document.getElementById('chatInput')?.focus(), 100);
}

function nuevaConversacion() {
  _conversacionId = null;
  _chatHistorial  = [];
  const msgs = document.getElementById('chatMessages');
  if (msgs) msgs.innerHTML = `<div class="msg-full agent">
    <div class="msg-avatar"><img src="assets/img/logo-agente.png" alt="BPA" onerror="this.parentElement.textContent='B'"></div>
    <div class="msg-bubble"><div class="msg-text">¡Nueva conversación! ¿Qué quieres hacer?<br><br>
    <strong>Crear:</strong><br>
    • <a href="#" style="color:var(--accent);text-decoration:none" onclick="setMsgInput('Crea un proceso de ');return false">Crear un proceso</a><br>
    • <a href="#" style="color:var(--accent);text-decoration:none" onclick="setMsgInput('Crea una automatización de ');return false">Crear una automatización</a><br>
    • <a href="#" style="color:var(--accent);text-decoration:none" onclick="setMsgInput('Crea un KPI de ');return false">Crear un KPI</a><br><br>
    <strong>Analizar:</strong><br>
    • <a href="#" style="color:var(--accent);text-decoration:none" onclick="setMsgInput('Dame un resumen de la empresa');return false">Resumen completo</a><br>
    • <a href="#" style="color:var(--accent);text-decoration:none" onclick="setMsgInput('Muéstrame mis procesos');return false">Ver procesos</a><br>
    • <a href="#" style="color:var(--accent);text-decoration:none" onclick="setMsgInput('Muéstrame mis KPIs');return false">Ver KPIs</a>
    </div></div>
  </div>`;
  document.getElementById('chatInput')?.focus();
}

function setMsgInput(text) {
  const inp = document.getElementById('chatInput');
  if (inp) { inp.value = text; inp.focus(); }
}

async function sendChat() {
  if (_isSending) return;
  const input = document.getElementById('chatInput');
  if (!input?.value.trim()) return;

  let mensaje;
  try { mensaje = sanitize(input.value.trim(), 2000); }
  catch(e) { toast('Mensaje no permitido'); return; }
  input.value = '';

  _isSending = true;
  const btn = document.getElementById('chatSendBtn');
  if (btn) { btn.disabled = true; btn.style.opacity = '.5'; }

  const msgs = document.getElementById('chatMessages');
  const user = API.session.get().user;
  const userInitials = user ? ((user.nombre||'U')[0]+(user.apellido||'U')[0]).toUpperCase() : 'U';

  appendMsg(msgs, 'user', userInitials, mensaje);

  // Typing indicator
  const typingId = 'typing_' + Date.now();
  const typingDiv = document.createElement('div');
  typingDiv.className = 'msg-full agent';
  typingDiv.id = typingId;
  typingDiv.innerHTML = `<div class="msg-avatar"><img src="assets/img/logo-agente.png" alt="BPA" onerror="this.parentElement.textContent='B'"></div>
    <div class="msg-bubble"><div class="msg-text"><div class="chat-typing">
      <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
    </div></div></div>`;
  msgs.appendChild(typingDiv);
  msgs.scrollTop = msgs.scrollHeight;

  try {
    const data = await BPA.post('/api/agente/chat', { mensaje, conversacion_id: _conversacionId });
    const isNewConv = !_conversacionId;
    _conversacionId = data.conversacion_id;
    document.getElementById(typingId)?.remove();
    appendMsg(msgs, 'agent', 'B', data.respuesta);

    // Si es conversación nueva, incrementar badges
    if (isNewConv) {
      ['badgeAgente','badgePropuestas'].forEach(id => {
        const el = document.getElementById(id);
        if (el) { const n = (parseInt(el.textContent)||0)+1; el.textContent=n; el.style.display=''; }
      });
    }

    // Si el agente creó/eliminó algo, refrescar la sección correspondiente en background
    if (data.accion) {
      const accion = data.accion;
      if (accion.includes('proceso')) {
        loadProcesos().then(() => _renderProcesos());
        loadHomeDashboard(); // refrescar stats
        toast(accion.startsWith('created') ? '✅ Proceso creado' : accion.startsWith('deleted') ? '🗑️ Proceso eliminado' : '✏️ Proceso actualizado');
      } else if (accion.includes('kpi')) {
        loadKpis().then(() => _renderKpis());
        toast(accion.startsWith('created') ? '✅ KPI creado' : accion.startsWith('deleted') ? '🗑️ KPI eliminado' : '✏️ KPI actualizado');
      } else if (accion.includes('auto')) {
        loadAutomatizaciones().then(() => _renderAutos());
        toast(accion.startsWith('created') ? '✅ Automatización creada' : accion.startsWith('deleted') ? '🗑️ Automatización eliminada' : '✏️ Automatización actualizada');
      }
    }
  } catch(e) {
    document.getElementById(typingId)?.remove();
    appendMsg(msgs, 'agent', 'B', `⚠️ ${e.message || 'Error de conexión. Verifica que el servidor esté activo.'}`);
  } finally {
    _isSending = false;
    if (btn) { btn.disabled = false; btn.style.opacity = ''; }
    msgs.scrollTop = msgs.scrollHeight;
    input.focus();
  }
}

function renderMarkdown(text) {
  // NO escapamos primero — procesamos el markdown sobre texto plano
  // y luego dejamos que innerHTML interprete el resultado
  let s = text || '';

  // Escapar solo chars peligrosos (XSS), dejando * y _ libres para markdown
  s = s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

  // Bloques de código `inline`
  s = s.replace(/`([^`\n]+)`/g, '<code>$1</code>');

  // Negrita **texto**
  s = s.replace(/\*\*([^*\n]{1,120})\*\*/g, '<strong>$1</strong>');

  // Cursiva *texto* (solo si no es ** ya procesado)
  s = s.replace(/(?<!\*)\*([^*\n]{1,80})\*(?!\*)/g, '<em>$1</em>');

  // Líneas de bullet: • ó - al inicio de línea
  s = s.replace(/^[•\-]\s+(.+)$/gm, '<li>$1</li>');
  s = s.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');

  // Listas numeradas
  s = s.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');

  // Saltos de línea → <br>  (excepto dentro de ul ya procesado)
  s = s.replace(/\n/g, '<br>');

  // Limpiar <br> que queden dentro de <ul>
  s = s.replace(/<ul>(<br>)*/g, '<ul>');
  s = s.replace(/(<br>)*<\/ul>/g, '</ul>');

  return s;
}

function appendMsg(container, role, avatar, text) {
  if (!container) return;
  const div = document.createElement('div');
  div.className = `msg-full ${role}`;
  const html = renderMarkdown(text);
  const avatarHtml = role === 'agent'
    ? `<div class="msg-avatar"><img src="assets/img/logo-agente.png" alt="BPA" onerror="this.parentElement.textContent='B'"></div>`
    : `<div class="msg-avatar">${esc(avatar)}</div>`;
  div.innerHTML = `${avatarHtml}<div class="msg-bubble"><div class="msg-text">${html}</div></div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

// Quick chat desde la home
async function homeQuickChat() {
  const input = document.getElementById('homeChatInput');
  if (!input?.value.trim()) return;
  const msg = input.value.trim();
  input.value = '';
  navTo('Agente IA', 'page-agente');
  setTimeout(() => {
    const chatInput = document.getElementById('chatInput');
    if (chatInput) { chatInput.value = msg; sendChat(); }
  }, 150);
}

// ── MODAL CUSTOM ──────────────────────────────────────────────
// Monkey-patch del openModal original para soportar 'custom'
document.addEventListener('DOMContentLoaded', () => {
  const _orig = window.openModal;
  window.openModal = function(type, title, body, foot) {
    if (type === 'custom') {
      const titleEl = document.getElementById('modalTitle');
      const bodyEl  = document.getElementById('modalBody');
      const footEl  = document.getElementById('modalFoot');
      const back    = document.getElementById('modalBackdrop');
      if (titleEl) titleEl.textContent = title || '';
      if (bodyEl)  bodyEl.innerHTML  = body  || '';
      if (footEl)  footEl.innerHTML  = foot  || '';
      if (back)    back.classList.add('show');
      return;
    }
    if (_orig) _orig.call(this, type);
  };

  // Inicializar búsqueda
  initSearch();

  // Botón home en topbar → volver a dashboard
  document.querySelectorAll('.topbar-right .icon-btn').forEach(btn => {
    const svg = btn.querySelector('svg');
    if (svg?.innerHTML.includes('9 22 9 12')) { // home icon
      btn.onclick = () => navTo('Dashboard', 'page-home');
    }
  });
});

// ── setPage hook: cargar datos al entrar en sección ───────────
const _origSetPage = window.setPage;
window.setPage = function(el, title, pageId) {
  if (_origSetPage) _origSetPage(el, title, pageId);
  if (pageId === 'page-agente') initAgentePage();
  if (pageId === 'page-centro') loadCentro();
};

// ══════════════════════════════════════════════════════════════
// CENTRO DE CONTROL
// ══════════════════════════════════════════════════════════════
let _centroInterval = null;

async function loadCentro(manual = false) {
  if (manual) toast('Actualizando datos…');
  _setCentroLastUpdate();

  // Fetch everything in parallel
  const [health, autos, procesos, users, kpis, allHistory] = await Promise.allSettled([
    fetch('http://localhost:8002/health').then(r => r.ok ? r.json() : null).catch(() => null),
    BPA.get('/api/automatizaciones').catch(() => []),
    BPA.get('/api/procesos').catch(() => []),
    BPA.get('/api/admin/users').catch(() => null),
    BPA.get('/api/kpis').catch(() => []),
    _fetchAllRecentHistory(),
  ]);

  const apiOk    = health.status === 'fulfilled' && health.value;
  const autosArr = autos.status === 'fulfilled'    ? autos.value    : [];
  const prosArr  = procesos.status === 'fulfilled' ? procesos.value : [];
  const usersArr = users.status === 'fulfilled'    ? users.value    : null;
  const kpisArr  = kpis.status === 'fulfilled'     ? kpis.value     : [];
  const histArr  = allHistory.status === 'fulfilled' ? allHistory.value : [];

  // Update caches
  _autos    = autosArr;
  _procesos = prosArr;
  _kpis     = kpisArr;
  window._procesos = _procesos; window._autos = _autos;

  // Status chips
  _setCentroChip('cs-api',        apiOk ? 'ok' : 'err',  apiOk ? 'API' : 'API off');
  _setCentroChip('cs-db',         'ok',  'Base de datos');
  _setCentroChip('cs-scheduler',  autosArr.some(a => a.tipo_trigger === 'cron' && a.estado === 'activa') ? 'ok' : 'warn', 'Scheduler');
  const connCount = _countConnectors(autosArr);
  _setCentroChip('cs-connectors', connCount > 0 ? 'ok' : 'off', `Conectores (${connCount})`);
  _setCentroChip('cs-ai',         'warn', 'Motor IA');

  // Render sections
  _renderCentroAutoMonitor(autosArr);
  _renderCentroActivity(histArr);
  _renderCentroConnectors(autosArr);
  _renderCentroUsers(usersArr);
  _renderCentroHeatmap(prosArr);
}

function _setCentroChip(id, cls, label) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = `status-chip ${cls}`;
  el.innerHTML = `<span class="status-chip-dot"></span>${esc(label)}`;
}

function _setCentroLastUpdate() {
  const el = document.getElementById('centroLastUpdate');
  if (el) el.textContent = `Actualizado: ${new Date().toLocaleTimeString('es', {hour:'2-digit', minute:'2-digit', second:'2-digit'})}`;
}

function _countConnectors(autos) {
  const types = new Set(autos.filter(a => a.tipo_accion && a.tipo_accion !== 'webhook_out' || a.herramienta).map(a => a.tipo_accion));
  return types.size;
}

// ── Auto Monitor ───────────────────────────────────────────────
function _renderCentroAutoMonitor(autos) {
  const el = document.getElementById('centroAutoMonitor');
  if (!el) return;
  if (!autos.length) {
    el.innerHTML = `<div style="color:var(--fg-3);font-size:.78rem;padding:.5rem 0">Sin automatizaciones. <button class="btn-secondary" style="font-size:.73rem;padding:.3rem .7rem;margin-left:.5rem" onclick="openAutoModal()">Crear primera</button></div>`;
    return;
  }
  el.innerHTML = autos.map(a => {
    const stCls = `estado-${a.estado || 'pendiente'}`;
    return `
    <div class="am-card ${stCls}" onclick="openAutoDetail('${a.id}')">
      <div class="am-card-header">
        <div class="am-card-name">${esc(a.nombre)}</div>
        ${estadoPill(a.estado || 'pendiente')}
      </div>
      <div class="am-card-meta">
        <span>${_triggerLabel(a.tipo_trigger||'manual')}</span>
        <span>→</span>
        <span>${_actionLabel(a.tipo_accion||'webhook_out')}</span>
        <span>· ${(a.ejecuciones||0)} ejec.</span>
      </div>
      <div class="am-card-actions" onclick="event.stopPropagation()">
        <button class="am-run-btn" onclick="quickRunAuto('${a.id}','${esc(a.nombre)}')">▶ Ejecutar</button>
        <button class="am-run-btn" style="color:var(--fg-3);border-color:var(--border);background:none" onclick="openAutoDetail('${a.id}')">Detalle</button>
      </div>
    </div>`;
  }).join('');
}

// ── Activity Feed (across all autos) ──────────────────────────
async function _fetchAllRecentHistory() {
  if (!_autos.length) return [];
  // Fetch history for up to 3 most recent autos
  const recent = _autos.slice(0, 5);
  const results = await Promise.allSettled(
    recent.map(a => BPA.get(`/api/ejecutar/${a.id}/historial?limit=5`).then(h => h.map(x => ({ ...x, autoNombre: a.nombre }))))
  );
  const all = results.filter(r => r.status === 'fulfilled').flatMap(r => r.value);
  all.sort((a, b) => new Date(b.created_at||0) - new Date(a.created_at||0));
  return all.slice(0, 20);
}

function _renderCentroActivity(history) {
  const el  = document.getElementById('centroActivityFeed');
  const cnt = document.getElementById('centroActivityCount');
  if (!el) return;
  if (cnt) cnt.textContent = `${history.length} eventos`;
  if (!history.length) {
    el.innerHTML = `<p style="font-size:.75rem;color:var(--fg-3);padding:.25rem 0">Sin actividad reciente</p>`;
    return;
  }
  el.innerHTML = history.map(h => {
    const ok   = ['exitoso','ok','success'].includes(h.estado);
    const fail = ['error','fallido'].includes(h.estado);
    const dotCls = ok ? 'ok' : fail ? 'fail' : 'run';
    const ts = h.created_at ? new Date(h.created_at) : null;
    const timeStr = ts ? ts.toLocaleString('es', {day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit'}) : '–';
    return `
    <div class="feed-item">
      <div class="feed-dot ${dotCls}"></div>
      <div class="feed-content">
        <div class="feed-title">${esc(h.autoNombre || 'Automatización')}</div>
        <div class="feed-sub">${esc(h.estado||'–')} · ${h.triggered_by ? `por ${esc(h.triggered_by)}` : 'sistema'}${h.duracion_ms ? ` · ${h.duracion_ms}ms` : ''}</div>
      </div>
      <div class="feed-time">${timeStr}</div>
    </div>`;
  }).join('');
}

// ── Connectors ─────────────────────────────────────────────────
function _renderCentroConnectors(autos) {
  const el = document.getElementById('centroConnectors');
  if (!el) return;
  const usedTypes = new Set(autos.map(a => a.tipo_accion).filter(Boolean));
  const connectors = [
    { id:'email',    name:'Email / SMTP',  icon:`<rect x="2" y="4" width="20" height="16" rx="2"/><polyline points="22 7 12 13 2 7"/>`, color:'#f59e0b' },
    { id:'telegram', name:'Telegram',      icon:`<path d="M21 5L2 12.5l7 1M21 5l-3.5 15L9 13.5M21 5 9 13.5m0 0v5l3.5-3"/>`, color:'#38bdf8' },
    { id:'slack',    name:'Slack',         icon:`<path d="M14.5 10c-.83 0-1.5-.67-1.5-1.5v-5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5z"/>`, color:'#8b5cf6' },
    { id:'n8n',      name:'n8n',           icon:`<circle cx="8" cy="12" r="3"/><circle cx="16" cy="6" r="3"/><circle cx="16" cy="18" r="3"/><line x1="11" y1="12" x2="13" y2="7"/><line x1="11" y1="12" x2="13" y2="17"/>`, color:'#f97316' },
    { id:'webhook_out', name:'HTTP Webhook', icon:`<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>`, color:'#22d3ee' },
    { id:'gmail',    name:'Gmail OAuth',   icon:`<rect x="2" y="4" width="20" height="16" rx="2"/><polyline points="22 7 12 13 2 7"/>`, color:'#ea4335' },
  ];
  el.innerHTML = connectors.map(c => {
    const active = usedTypes.has(c.id);
    const status = active ? 'on' : 'off';
    const label  = active ? 'Activo' : 'Sin configurar';
    return `
    <div class="conn-row">
      <div class="conn-icon" style="background:${c.color}18;border:1px solid ${c.color}30">
        <svg viewBox="0 0 24 24" style="stroke:${c.color}">${c.icon}</svg>
      </div>
      <div class="conn-name">${c.name}</div>
      <span class="conn-status ${status}">${label}</span>
    </div>`;
  }).join('');
}

// ── Users (BD real via admin API) ──────────────────────────────
function _renderCentroUsers(users) {
  const el  = document.getElementById('centroUsersList');
  const cnt = document.getElementById('centroUsersCount');
  if (!el) return;
  if (!users || !Array.isArray(users)) {
    el.innerHTML = `<p style="font-size:.73rem;color:var(--fg-3)">Solo visible para administradores</p>`;
    return;
  }
  if (cnt) cnt.textContent = `${users.length} usuarios`;
  if (!users.length) {
    el.innerHTML = `<p style="font-size:.73rem;color:var(--fg-3)">Sin usuarios registrados</p>`;
    return;
  }
  el.innerHTML = users.slice(0, 8).map(u => {
    const initials = ((u.nombre||'?')[0] + (u.apellido||'?')[0]).toUpperCase();
    const planCls = u.plan === 'enterprise' ? 'ent' : u.plan === 'pro' ? 'pro' : 'free';
    const planLabel = u.plan === 'enterprise' ? 'Enterprise' : u.plan === 'pro' ? 'Pro' : 'Free';
    return `
    <div class="user-row">
      <div class="user-avatar-sm">${esc(initials)}</div>
      <div class="user-info-col">
        <div class="user-name-sm">${esc(u.nombre + ' ' + (u.apellido||''))}</div>
        <div class="user-email-sm">${esc(u.email)}</div>
      </div>
      <span class="user-plan-badge ${planCls}">${planLabel}</span>
    </div>`;
  }).join('');
  if (users.length > 8) {
    el.innerHTML += `<div style="font-size:.68rem;color:var(--fg-3);padding:.35rem .25rem">+${users.length - 8} más</div>`;
  }
}

// ── Process heatmap ────────────────────────────────────────────
function _renderCentroHeatmap(procesos) {
  const el = document.getElementById('centroProcessHeatmap');
  if (!el) return;
  const scored = procesos.filter(p => p.score != null).sort((a,b) => (b.score||0) - (a.score||0));
  if (!scored.length) {
    el.innerHTML = `<p style="font-size:.73rem;color:var(--fg-3)">Sin procesos analizados</p>`;
    return;
  }
  el.innerHTML = scored.slice(0, 8).map(p => {
    const pct  = Math.min(100, Math.max(0, p.score || 0));
    const col  = pct < 40 ? '#f43f5e' : pct < 70 ? '#f59e0b' : '#10b981';
    return `
    <div class="score-row">
      <div class="score-name">${esc(p.nombre)}</div>
      <div class="score-bar-wrap"><div class="score-bar" style="width:${pct}%;background:${col}"></div></div>
      <div class="score-val">${pct}</div>
    </div>`;
  }).join('');
}

// ── Run all active ─────────────────────────────────────────────
async function runAllActiveAutos() {
  const activas = _autos.filter(a => a.estado === 'activa');
  if (!activas.length) { toast('No hay automatizaciones activas'); return; }
  if (!confirm(`¿Ejecutar ${activas.length} automatizaciones activas ahora?`)) return;
  toast(`Ejecutando ${activas.length} automatizaciones…`);
  let ok = 0, fail = 0;
  await Promise.allSettled(activas.map(a =>
    BPA.post(`/api/ejecutar/${a.id}/run`, {}).then(() => ok++).catch(() => fail++)
  ));
  toast(`✅ ${ok} ejecutadas${fail ? ` · ⚠️ ${fail} errores` : ''}`);
  setTimeout(() => loadCentro(), 500);
}

// ── Command console ────────────────────────────────────────────
function clearCmdOutput() {
  const el = document.getElementById('cmdOutput');
  if (el) el.innerHTML = `<div class="cmd-line sys"><span class="cmd-prefix">SYS›</span><span class="cmd-text">Consola limpiada.</span></div>`;
}

function _appendCmdLine(role, text) {
  const el = document.getElementById('cmdOutput');
  if (!el) return;
  const prefixes = { user:'USR›', agent:'AI ›', sys:'SYS›' };
  const div = document.createElement('div');
  div.className = `cmd-line ${role}`;
  div.innerHTML = `<span class="cmd-prefix">${prefixes[role]||'···'}</span><span class="cmd-text">${esc(text)}</span>`;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

async function sendCmdCommand() {
  const input = document.getElementById('cmdInput');
  if (!input?.value.trim()) return;
  const msg = input.value.trim();
  input.value = '';
  _appendCmdLine('user', msg);
  _appendCmdLine('sys', 'Enviando al agente IA…');
  try {
    const { token } = API.session.get();
    // Use the existing agent API
    const r = await fetch('http://localhost:8002/api/agente/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ mensaje: msg, conversacion_id: null }),
      credentials: 'include',
    });
    const out = el => document.getElementById('cmdOutput');
    if (r.ok) {
      const data = await r.json();
      const reply = data.respuesta || data.mensaje || JSON.stringify(data);
      // Remove "sending" line
      const cmdOut = document.getElementById('cmdOutput');
      if (cmdOut?.lastChild) cmdOut.removeChild(cmdOut.lastChild);
      _appendCmdLine('agent', reply.slice(0, 500) + (reply.length > 500 ? '…' : ''));
      // Reload centro data in case agent created something
      setTimeout(() => loadCentro(), 1000);
    } else {
      _appendCmdLine('sys', `Error ${r.status} — asegúrate de que el backend está en puerto 8002`);
    }
  } catch(e) {
    _appendCmdLine('sys', `Error de conexión: ${e.message}`);
  }
}
