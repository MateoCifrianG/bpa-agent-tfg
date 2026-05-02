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
    const r = await fetch('http://localhost:8001' + path, {
      headers: { Authorization: `Bearer ${token}` },
      credentials: 'include',
    });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  },
  async post(path, body) {
    const { token } = API.session.get();
    const r = await fetch('http://localhost:8001' + path, {
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
    const r = await fetch('http://localhost:8001' + path, {
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
    const r = await fetch('http://localhost:8001' + path, {
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

function initSearch() {
  const btn = document.querySelector('.topbar-search');
  if (!btn) return;
  btn.onclick = openSearch;
  document.addEventListener('keydown', e => {
    if ((e.metaKey||e.ctrlKey) && e.key==='k') { e.preventDefault(); openSearch(); }
    if (e.key==='Escape') closeSearch();
  });
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
          <button class="icon-action" title="Editar" onclick='openProcesoModal(${JSON.stringify(p)})'>${ICONS.edit}</button>
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
    el.innerHTML = emptyState(ICONS.auto, 'Sin automatizaciones', 'Crea automatizaciones para que el agente las ejecute y ahorre tiempo en tus procesos.');
    return;
  }
  el.innerHTML = `<table class="data-table">
    <thead><tr><th>Nombre</th><th>Herramienta</th><th>Estado</th><th>Ejecuciones</th><th>Ahorro/mes</th><th></th></tr></thead>
    <tbody>${_autos.map(a => `<tr>
      <td><strong>${esc(a.nombre)}</strong>${a.descripcion?`<br><span style="font-size:.72rem;color:var(--fg-3)">${esc(a.descripcion.slice(0,70))}${a.descripcion.length>70?'…':''}</span>`:''}</td>
      <td>${a.herramienta?`<span class="tool-tag">${esc(a.herramienta)}</span>`:'–'}</td>
      <td>${estadoPill(a.estado)}</td>
      <td>${a.ejecuciones.toLocaleString()}</td>
      <td>${a.horas_mes?a.horas_mes+' h':'–'}</td>
      <td><div style="display:flex;gap:.4rem">
        <button class="icon-action" title="Editar" onclick='openAutoModal(${JSON.stringify(a)})'>${ICONS.edit}</button>
        <button class="icon-action danger" title="Eliminar" onclick="deleteAuto('${a.id}','${esc(a.nombre)}')">${ICONS.trash}</button>
      </div></td>
    </tr>`).join('')}</tbody>
  </table>`;
}

function openAutoModal(data) {
  const isEdit = data?.id;
  const body = `<div class="form-grid">
    <div class="field-group" style="grid-column:1/-1">
      <label class="field-label">Nombre *</label>
      <input class="field-input" id="aNombre" maxlength="255" value="${esc(isEdit?data.nombre:'')}" placeholder="Ej: Envío automático de contrato"/>
    </div>
    <div class="field-group" style="grid-column:1/-1">
      <label class="field-label">Descripción</label>
      <textarea class="field-textarea" id="aDesc" maxlength="1000" placeholder="¿Qué hace esta automatización?">${esc(isEdit?(data.descripcion||''):'')}</textarea>
    </div>
    <div class="field-group">
      <label class="field-label">Herramienta</label>
      <input class="field-input" id="aHerr" maxlength="100" value="${esc(isEdit?(data.herramienta||''):'')}" placeholder="n8n, Gmail, Drive…"/>
    </div>
    <div class="field-group">
      <label class="field-label">Estado</label>
      <select class="field-select" id="aEstado">
        ${['activa','pendiente','pausada','error'].map(e=>`<option value="${e}" ${isEdit&&data.estado===e?'selected':''}>${e[0].toUpperCase()+e.slice(1)}</option>`).join('')}
      </select>
    </div>
    <div class="field-group">
      <label class="field-label">Horas ahorradas / mes</label>
      <input class="field-input" id="aHoras" type="number" min="0" max="10000" value="${isEdit?(data.horas_mes||''):''}" placeholder="Ej: 8"/>
    </div>
    <div class="field-group">
      <label class="field-label">Ejecuciones totales</label>
      <input class="field-input" id="aEjec" type="number" min="0" value="${isEdit?(data.ejecuciones||0):0}"/>
    </div>
  </div>`;
  const foot = `<button class="btn-secondary" onclick="closeModal()">Cancelar</button>
    <button class="btn-cta" onclick="saveAuto(${isEdit?`'${data.id}'`:'null'})">${isEdit?'Guardar cambios':'Crear automatización'}</button>`;
  openModal('custom', isEdit?'Editar automatización':'Nueva automatización', body, foot);
  setTimeout(() => document.getElementById('aNombre')?.focus(), 50);
}

async function saveAuto(id) {
  try {
    const nombre = sanitize(document.getElementById('aNombre')?.value || '', 255);
    if (!nombre) { toast('El nombre es obligatorio'); return; }
    const payload = {
      nombre,
      descripcion: sanitize(document.getElementById('aDesc')?.value || '', 1000) || null,
      herramienta: sanitize(document.getElementById('aHerr')?.value || '', 100) || null,
      estado:      document.getElementById('aEstado')?.value || 'pendiente',
      horas_mes:   parseInt(document.getElementById('aHoras')?.value) || null,
      ejecuciones: parseInt(document.getElementById('aEjec')?.value) || 0,
    };
    if (id) { await BPA.put(`/api/automatizaciones/${id}`, payload); toast('Automatización actualizada'); }
    else     { await BPA.post('/api/automatizaciones', payload);      toast('Automatización creada'); }
    closeModal();
    await loadAutomatizaciones();
    await loadHomeDashboard();
  } catch(e) { toast(e.message || 'Error al guardar'); }
}

async function deleteAuto(id, nombre) {
  if (!confirm(`¿Eliminar la automatización "${nombre}"?\nEsta acción no se puede deshacer.`)) return;
  try {
    await BPA.del(`/api/automatizaciones/${id}`);
    toast('Automatización eliminada');
    await loadAutomatizaciones();
    await loadHomeDashboard();
  } catch(e) { toast(e.message || 'Error al eliminar'); }
}

// ── KPIs ─────────────────────────────────────────────────────
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

function _renderKpis() {
  const el = document.getElementById('kpisList');
  if (!el) return;
  if (!_kpis.length) {
    el.innerHTML = emptyState(ICONS.kpi, 'Sin KPIs', 'Añade indicadores de rendimiento para hacer seguimiento de la evolución de tu empresa.');
    return;
  }
  const tendIcon = t => t==='up'?'↑':t==='down'?'↓':'→';
  const tendCol  = t => t==='up'?'var(--emerald)':t==='down'?'var(--rose)':'var(--amber)';
  el.innerHTML = `<div class="cards-grid">${_kpis.map(k => `
    <div class="card-item">
      <div class="card-item-header">
        <div>
          <div class="card-item-title">${esc(k.nombre)}</div>
          ${k.categoria?`<div class="card-item-sub">${esc(k.categoria)}</div>`:''}
        </div>
        <span style="font-size:1.4rem;font-weight:700;color:${tendCol(k.tendencia)}">${tendIcon(k.tendencia)}</span>
      </div>
      <div style="font-size:1.6rem;font-weight:700;color:var(--fg);margin:.4rem 0">${esc(k.valor)}${k.unidad?`<span style="font-size:.85rem;font-weight:400;color:var(--fg-3);margin-left:.3rem">${esc(k.unidad)}</span>`:''}</div>
      ${k.objetivo?`<div style="font-size:.72rem;color:var(--fg-3)">Objetivo: ${esc(k.objetivo)}</div>`:''}
      <div class="card-item-actions">
        <button class="icon-action" title="Editar" onclick='openKpiModal(${JSON.stringify(k)})'>${ICONS.edit}</button>
        <button class="icon-action danger" title="Eliminar" onclick="deleteKpi('${k.id}','${esc(k.nombre)}')">${ICONS.trash}</button>
      </div>
    </div>`).join('')}
  </div>`;
}

function openKpiModal(data) {
  const isEdit = data?.id;
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
        ${[['up','↑ Subiendo'],['down','↓ Bajando'],['flat','→ Estable']].map(([v,l])=>`<option value="${v}" ${isEdit&&data.tendencia===v?'selected':''}>${l}</option>`).join('')}
      </select>
    </div>
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
    if (!nombre || !valor) { toast('Nombre y valor son obligatorios'); return; }
    const payload = {
      nombre, valor,
      unidad:    sanitize(document.getElementById('kUnidad')?.value || '', 50)  || null,
      objetivo:  sanitize(document.getElementById('kObj')?.value    || '', 100) || null,
      categoria: document.getElementById('kCat')?.value  || null,
      tendencia: document.getElementById('kTend')?.value || 'flat',
    };
    if (id) { await BPA.put(`/api/kpis/${id}`, payload); toast('KPI actualizado'); }
    else     { await BPA.post('/api/kpis', payload);      toast('KPI creado'); }
    closeModal();
    await loadKpis();
    await loadHomeDashboard();
  } catch(e) { toast(e.message || 'Error al guardar'); }
}

async function deleteKpi(id, nombre) {
  if (!confirm(`¿Eliminar el KPI "${nombre}"?`)) return;
  try {
    await BPA.del(`/api/kpis/${id}`);
    toast('KPI eliminado');
    await loadKpis();
    await loadHomeDashboard();
  } catch(e) { toast(e.message || 'Error al eliminar'); }
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
    msgs.forEach(m => appendMsg(container, m.role==='user'?'user':'agent', m.role==='user'?userInitials:'B', m.content));
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
  // Si hay conversación activa, cargarla
  if (_conversacionId) {
    await _loadConversacionHistorial(_conversacionId);
  }
  // Focus input
  setTimeout(() => document.getElementById('chatInput')?.focus(), 100);
}

function nuevaConversacion() {
  _conversacionId = null;
  _chatHistorial  = [];
  const msgs = document.getElementById('chatMessages');
  if (msgs) msgs.innerHTML = `<div class="msg-full agent">
    <div class="msg-avatar">B</div>
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
// Sobreescribir para cargar historial cuando se abre el chat
const _origSetPage = window.setPage;
window.setPage = function(el, title, pageId) {
  if (_origSetPage) _origSetPage(el, title, pageId);
  if (pageId === 'page-agente') initAgentePage();
};
