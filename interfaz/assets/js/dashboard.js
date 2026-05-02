// dashboard.js — Lógica de datos reales para BPA-Agent dashboard

// ── Helpers ──────────────────────────────────────────────────
function scoreClass(s) {
  if (s === null || s === undefined) return 'none';
  if (s < 40) return 'low';
  if (s < 70) return 'mid';
  return 'good';
}

function scoreColor(s) {
  if (s === null || s === undefined) return 'var(--fg-3)';
  if (s < 40) return 'var(--rose)';
  if (s < 70) return 'var(--amber)';
  return 'var(--emerald)';
}

function estadoPill(estado) {
  const map = {
    activa:    '<span class="status-pill active"><span class="status-dot"></span>Activa</span>',
    pendiente: '<span class="status-pill pending"><span class="status-dot"></span>Pendiente</span>',
    pausada:   '<span class="status-pill paused"><span class="status-dot"></span>Pausada</span>',
    error:     '<span class="status-pill error"><span class="status-dot"></span>Error</span>',
    analizado: '<span class="status-pill active"><span class="status-dot"></span>Analizado</span>',
    critico:   '<span class="status-pill error"><span class="status-dot"></span>Crítico</span>',
    optimizado:'<span class="status-pill active"><span class="status-dot"></span>Optimizado</span>',
  };
  return map[estado] || `<span class="status-pill pending"><span class="status-dot"></span>${estado}</span>`;
}

function emptyState(icon, title, desc) {
  return `<div class="empty-state">
    ${icon}
    <h3>${title}</h3>
    <p>${desc}</p>
  </div>`;
}

const ICON_PROCESO = `<svg viewBox="0 0 24 24"><circle cx="12" cy="5" r="3"/><circle cx="5" cy="19" r="3"/><circle cx="19" cy="19" r="3"/><path d="M12 8v3M8.25 16.5 12 11M15.75 16.5 12 11"/></svg>`;
const ICON_AUTO    = `<svg viewBox="0 0 24 24"><path d="m13 2-2 2.5h3L12 7"/><path d="M10 14v-3a2 2 0 0 1 4 0v3"/><path d="M6 14a2 2 0 0 0-2 2v2h16v-2a2 2 0 0 0-2-2"/><path d="M14 14H10"/></svg>`;
const ICON_KPI     = `<svg viewBox="0 0 24 24"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>`;
const ICON_TRASH   = `<svg viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>`;
const ICON_EDIT    = `<svg viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`;

// ── Cache de datos ────────────────────────────────────────────
let _procesos = [];
let _autos = [];
let _kpis = [];
let _empresa = null;
let _conversacionId = null;

// ── HOME DASHBOARD ────────────────────────────────────────────
async function loadHomeDashboard() {
  try {
    const [procesos, autos, kpis, empresa] = await Promise.all([
      API._fetch('/api/procesos'),
      API._fetch('/api/automatizaciones'),
      API._fetch('/api/kpis'),
      API._fetch('/api/empresa/mia').catch(() => null),
    ]);

    _procesos = procesos.ok ? await procesos.json() : [];
    _autos    = autos.ok    ? await autos.json()    : [];
    _kpis     = kpis.ok     ? await kpis.json()     : [];
    _empresa  = empresa && empresa.ok ? await empresa.json() : null;

    // KPI cards
    const activasCnt = _autos.filter(a => a.estado === 'activa').length;
    const horasTot = _autos.reduce((s, a) => s + (a.horas_mes || 0), 0);
    const scores = _procesos.filter(p => p.score !== null).map(p => p.score);
    const avgScore = scores.length ? Math.round(scores.reduce((a,b) => a+b, 0) / scores.length) : null;

    setText('statProcesos', _procesos.length);
    setText('statProcesosub', _procesos.length === 0 ? 'Sin procesos aún' : `${_procesos.length} proceso${_procesos.length !== 1 ? 's' : ''} registrado${_procesos.length !== 1 ? 's' : ''}`);

    setText('statAutos', _autos.length);
    setText('statAutosub', `${activasCnt} activa${activasCnt !== 1 ? 's' : ''} · ${_autos.length - activasCnt} pendiente${_autos.length - activasCnt !== 1 ? 's' : ''}`);

    setText('statHoras', horasTot > 0 ? horasTot + 'h' : '–');
    setText('statHorasub', horasTot > 0 ? 'horas ahorradas al mes' : 'Sin automatizaciones activas aún');

    setText('statScore', avgScore !== null ? avgScore : '–');
    setText('statScoresub', avgScore !== null ? `Promedio de ${scores.length} proceso${scores.length !== 1 ? 's' : ''} · Objetivo: 80` : 'Sin scores aún');

    // Welcome summary
    const pendAutos = _autos.filter(a => a.estado === 'pendiente').length;
    const wSummary = document.getElementById('welcomeSummary');
    if (wSummary) {
      if (_procesos.length === 0 && _autos.length === 0) {
        wSummary.innerHTML = 'Empieza añadiendo tus <strong style="color:var(--fg)">procesos de negocio</strong> para que el agente pueda analizarlos.';
      } else {
        wSummary.innerHTML = `Tienes <strong style="color:var(--fg)">${_procesos.length} proceso${_procesos.length !== 1 ? 's' : ''}</strong> mapeado${_procesos.length !== 1 ? 's' : ''} y <strong style="color:var(--fg)">${activasCnt} automatización${activasCnt !== 1 ? 'es' : ''}</strong> activa${activasCnt !== 1 ? 's' : ''} generando valor.`;
      }
    }

    // Procesos list en home
    const pList = document.getElementById('homeProcesos');
    if (pList) {
      if (_procesos.length === 0) {
        pList.innerHTML = '<div style="padding:.75rem;color:var(--fg-3);font-size:.8rem">No hay procesos aún. <a href="#" onclick="setPage(document.querySelector(\'[data-page=Procesos]\'),\'Procesos\',\'page-procesos\');return false" style="color:var(--accent)">Añadir →</a></div>';
      } else {
        const sorted = [..._procesos].sort((a,b) => (a.score??100) - (b.score??100)).slice(0, 5);
        pList.innerHTML = sorted.map((p, i) => {
          const s = p.score ?? null;
          const w = s !== null ? s : 50;
          const col = scoreColor(s);
          return `<div class="process-item">
            <span class="proc-rank">${i+1}</span>
            <span class="proc-name">${escHtml(p.nombre)}</span>
            <div class="proc-bar-wrap"><div class="proc-bar" style="width:${w}%;background:${col};color:${col}"></div></div>
            <span class="proc-score" style="color:${col}">${s !== null ? s : '–'}</span>
          </div>`;
        }).join('');
      }
    }

    // Empresa info
    const eInfo = document.getElementById('homeEmpresaInfo');
    if (eInfo && _empresa) {
      eInfo.innerHTML = [
        { color:'var(--accent)',  title: _empresa.nombre, sub: _empresa.sector || 'Sector no especificado' },
        { color:'var(--indigo)',  title: `${_empresa.empleados ?? '–'} empleados`, sub: _empresa.ciudad || 'Ciudad no especificada' },
        { color:'var(--amber)',   title: `${_kpis.length} KPI${_kpis.length !== 1 ? 's' : ''}`, sub: 'indicadores de rendimiento' },
      ].map(item => `<div class="activity-item">
        <div class="act-dot" style="background:${item.color}"></div>
        <div class="act-text"><div class="act-title">${escHtml(item.title)}</div><div class="act-meta">${escHtml(item.sub)}</div></div>
      </div>`).join('');
    } else if (eInfo) {
      eInfo.innerHTML = '<div class="activity-item"><div class="act-dot" style="background:var(--fg-3);box-shadow:none"></div><div class="act-text"><div class="act-title">Sin datos de empresa</div></div></div>';
    }

    // Automatizaciones table en home
    const aTbody = document.getElementById('homeAutosTbody');
    if (aTbody) {
      if (_autos.length === 0) {
        aTbody.innerHTML = '<tr><td colspan="3" style="color:var(--fg-3);font-size:.8rem;padding:.75rem">Sin automatizaciones. <a href="#" onclick="setPage(document.querySelector(\'[data-page=Automatizaciones]\'),\'Automatizaciones\',\'page-automatizaciones\');return false" style="color:var(--accent)">Crear →</a></td></tr>';
      } else {
        aTbody.innerHTML = _autos.slice(0, 4).map(a =>
          `<tr>
            <td>${escHtml(a.nombre)}</td>
            <td>${a.herramienta ? `<span class="tool-tag">${escHtml(a.herramienta)}</span>` : '–'}</td>
            <td>${estadoPill(a.estado)}</td>
          </tr>`
        ).join('');
      }
    }

  } catch (err) {
    console.error('Error cargando dashboard:', err);
  }
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function escHtml(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── PROCESOS ─────────────────────────────────────────────────
async function loadProcesos() {
  const container = document.getElementById('procesosList');
  if (!container) return;
  container.innerHTML = '<div class="loading-row"><div class="spinner"></div></div>';
  try {
    const r = await API._fetch('/api/procesos');
    _procesos = r.ok ? await r.json() : [];
    renderProcesos();
  } catch(e) {
    container.innerHTML = '<div class="empty-state"><p>Error cargando procesos.</p></div>';
  }
}

function renderProcesos() {
  const container = document.getElementById('procesosList');
  if (!container) return;
  if (_procesos.length === 0) {
    container.innerHTML = emptyState(ICON_PROCESO, 'Sin procesos', 'Añade tu primer proceso para que el agente IA pueda analizarlo y proponer automatizaciones.');
    return;
  }
  container.innerHTML = `
    <table class="data-table">
      <thead><tr>
        <th>Proceso</th><th>Responsable</th><th>Frecuencia</th>
        <th>Duración</th><th>Score</th><th>Estado</th><th></th>
      </tr></thead>
      <tbody>
        ${_procesos.map(p => {
          const s = p.score;
          return `<tr>
            <td><strong>${escHtml(p.nombre)}</strong>${p.descripcion ? `<br><span style="font-size:.72rem;color:var(--fg-3)">${escHtml(p.descripcion.substring(0,60))}${p.descripcion.length>60?'…':''}</span>` : ''}</td>
            <td>${escHtml(p.responsable || '–')}</td>
            <td>${escHtml(p.frecuencia || '–')}</td>
            <td>${p.duracion_h ? p.duracion_h + ' h/mes' : '–'}</td>
            <td>
              <div class="score-badge ${scoreClass(s)}">${s ?? '–'}</div>
            </td>
            <td>${estadoPill(p.estado)}</td>
            <td>
              <div style="display:flex;gap:.4rem">
                <button class="icon-action" title="Editar" onclick="openProcesoModal(${JSON.stringify(p).replace(/"/g,'&quot;')})">${ICON_EDIT}</button>
                <button class="icon-action danger" title="Eliminar" onclick="deleteProceso('${p.id}','${escHtml(p.nombre)}')">${ICON_TRASH}</button>
              </div>
            </td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;
}

function openProcesoModal(data) {
  const isEdit = data && data.id;
  const title = isEdit ? 'Editar proceso' : 'Nuevo proceso';
  const body = `
    <div class="form-grid">
      <div class="field-group" style="grid-column:1/-1">
        <label class="field-label">Nombre del proceso *</label>
        <input class="field-input" id="pNombre" value="${escHtml(isEdit ? data.nombre : '')}" placeholder="Ej: Onboarding de clientes"/>
      </div>
      <div class="field-group" style="grid-column:1/-1">
        <label class="field-label">Descripción</label>
        <textarea class="field-textarea" id="pDesc" placeholder="Describe brevemente el proceso…">${escHtml(isEdit ? (data.descripcion||'') : '')}</textarea>
      </div>
      <div class="field-group">
        <label class="field-label">Responsable</label>
        <input class="field-input" id="pResp" value="${escHtml(isEdit ? (data.responsable||'') : '')}" placeholder="Nombre o departamento"/>
      </div>
      <div class="field-group">
        <label class="field-label">Frecuencia</label>
        <select class="field-select" id="pFrec">
          <option value="">— Seleccionar —</option>
          ${['diario','semanal','quincenal','mensual','trimestral','esporádico'].map(f =>
            `<option value="${f}" ${isEdit && data.frecuencia === f ? 'selected' : ''}>${f.charAt(0).toUpperCase()+f.slice(1)}</option>`
          ).join('')}
        </select>
      </div>
      <div class="field-group">
        <label class="field-label">Duración estimada (h/mes)</label>
        <input class="field-input" id="pDur" type="number" min="0" value="${isEdit ? (data.duracion_h||'') : ''}" placeholder="Ej: 8"/>
      </div>
      <div class="field-group">
        <label class="field-label">Score actual (0-100)</label>
        <input class="field-input" id="pScore" type="number" min="0" max="100" value="${isEdit ? (data.score??'') : ''}" placeholder="Ej: 65"/>
      </div>
      <div class="field-group">
        <label class="field-label">Estado</label>
        <select class="field-select" id="pEstado">
          ${['pendiente','analizado','critico','optimizado'].map(e =>
            `<option value="${e}" ${isEdit && data.estado === e ? 'selected' : ''}>${e.charAt(0).toUpperCase()+e.slice(1)}</option>`
          ).join('')}
        </select>
      </div>
    </div>`;
  const foot = `<button class="btn-secondary" onclick="closeModal()">Cancelar</button>
    <button class="btn-cta" onclick="saveProceso(${isEdit ? `'${data.id}'` : 'null'})">${isEdit ? 'Guardar cambios' : 'Crear proceso'}</button>`;
  openModal('custom', title, body, foot);
}

async function saveProceso(id) {
  const nombre = document.getElementById('pNombre').value.trim();
  if (!nombre) { toast('El nombre es obligatorio'); return; }
  const payload = {
    nombre,
    descripcion: document.getElementById('pDesc').value.trim() || null,
    responsable: document.getElementById('pResp').value.trim() || null,
    frecuencia:  document.getElementById('pFrec').value || null,
    duracion_h:  parseInt(document.getElementById('pDur').value) || null,
    score:       parseInt(document.getElementById('pScore').value) || null,
    estado:      document.getElementById('pEstado').value,
  };
  try {
    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/procesos/${id}` : '/api/procesos';
    const r = await API._fetch(url, { method, headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    if (!r.ok) { const e = await r.json(); toast(e.detail || 'Error al guardar'); return; }
    toast(id ? 'Proceso actualizado' : 'Proceso creado');
    closeModal();
    loadProcesos();
    loadHomeDashboard();
  } catch(e) { toast('Error de red'); }
}

async function deleteProceso(id, nombre) {
  if (!confirm(`¿Eliminar el proceso "${nombre}"?`)) return;
  try {
    const r = await API._fetch(`/api/procesos/${id}`, { method: 'DELETE' });
    if (r.ok || r.status === 204) {
      toast('Proceso eliminado');
      loadProcesos();
      loadHomeDashboard();
    } else { toast('Error al eliminar'); }
  } catch(e) { toast('Error de red'); }
}

// ── AUTOMATIZACIONES ──────────────────────────────────────────
async function loadAutomatizaciones() {
  const container = document.getElementById('autosList');
  if (!container) return;
  container.innerHTML = '<div class="loading-row"><div class="spinner"></div></div>';
  try {
    const r = await API._fetch('/api/automatizaciones');
    _autos = r.ok ? await r.json() : [];
    renderAutomatizaciones();
  } catch(e) {
    container.innerHTML = '<div class="empty-state"><p>Error cargando automatizaciones.</p></div>';
  }
}

function renderAutomatizaciones() {
  const container = document.getElementById('autosList');
  if (!container) return;
  if (_autos.length === 0) {
    container.innerHTML = emptyState(ICON_AUTO, 'Sin automatizaciones', 'Crea automatizaciones para que el agente las ejecute y ahorre tiempo en tus procesos.');
    return;
  }
  container.innerHTML = `
    <table class="data-table">
      <thead><tr>
        <th>Nombre</th><th>Herramienta</th><th>Estado</th>
        <th>Ejecuciones</th><th>Ahorro/mes</th><th></th>
      </tr></thead>
      <tbody>
        ${_autos.map(a => `<tr>
          <td><strong>${escHtml(a.nombre)}</strong>${a.descripcion ? `<br><span style="font-size:.72rem;color:var(--fg-3)">${escHtml(a.descripcion.substring(0,60))}${a.descripcion.length>60?'…':''}</span>` : ''}</td>
          <td>${a.herramienta ? `<span class="tool-tag">${escHtml(a.herramienta)}</span>` : '–'}</td>
          <td>${estadoPill(a.estado)}</td>
          <td>${a.ejecuciones}</td>
          <td>${a.horas_mes ? a.horas_mes + ' h' : '–'}</td>
          <td>
            <div style="display:flex;gap:.4rem">
              <button class="icon-action" title="Editar" onclick="openAutoModal(${JSON.stringify(a).replace(/"/g,'&quot;')})">${ICON_EDIT}</button>
              <button class="icon-action danger" title="Eliminar" onclick="deleteAuto('${a.id}','${escHtml(a.nombre)}')">${ICON_TRASH}</button>
            </div>
          </td>
        </tr>`).join('')}
      </tbody>
    </table>`;
}

function openAutoModal(data) {
  const isEdit = data && data.id;
  const body = `
    <div class="form-grid">
      <div class="field-group" style="grid-column:1/-1">
        <label class="field-label">Nombre *</label>
        <input class="field-input" id="aNombre" value="${escHtml(isEdit ? data.nombre : '')}" placeholder="Ej: Envío automático de contrato"/>
      </div>
      <div class="field-group" style="grid-column:1/-1">
        <label class="field-label">Descripción</label>
        <textarea class="field-textarea" id="aDesc" placeholder="¿Qué hace esta automatización?">${escHtml(isEdit ? (data.descripcion||'') : '')}</textarea>
      </div>
      <div class="field-group">
        <label class="field-label">Herramienta</label>
        <input class="field-input" id="aHerr" value="${escHtml(isEdit ? (data.herramienta||'') : '')}" placeholder="n8n, Gmail, Drive…"/>
      </div>
      <div class="field-group">
        <label class="field-label">Estado</label>
        <select class="field-select" id="aEstado">
          ${['activa','pendiente','pausada','error'].map(e =>
            `<option value="${e}" ${isEdit && data.estado === e ? 'selected' : ''}>${e.charAt(0).toUpperCase()+e.slice(1)}</option>`
          ).join('')}
        </select>
      </div>
      <div class="field-group">
        <label class="field-label">Horas ahorradas / mes</label>
        <input class="field-input" id="aHoras" type="number" min="0" value="${isEdit ? (data.horas_mes||'') : ''}" placeholder="Ej: 8"/>
      </div>
      <div class="field-group">
        <label class="field-label">Ejecuciones totales</label>
        <input class="field-input" id="aEjec" type="number" min="0" value="${isEdit ? (data.ejecuciones||0) : '0'}"/>
      </div>
    </div>`;
  const foot = `<button class="btn-secondary" onclick="closeModal()">Cancelar</button>
    <button class="btn-cta" onclick="saveAuto(${isEdit ? `'${data.id}'` : 'null'})">${isEdit ? 'Guardar cambios' : 'Crear automatización'}</button>`;
  openModal('custom', isEdit ? 'Editar automatización' : 'Nueva automatización', body, foot);
}

async function saveAuto(id) {
  const nombre = document.getElementById('aNombre').value.trim();
  if (!nombre) { toast('El nombre es obligatorio'); return; }
  const payload = {
    nombre,
    descripcion: document.getElementById('aDesc').value.trim() || null,
    herramienta: document.getElementById('aHerr').value.trim() || null,
    estado:      document.getElementById('aEstado').value,
    horas_mes:   parseInt(document.getElementById('aHoras').value) || null,
    ejecuciones: parseInt(document.getElementById('aEjec').value) || 0,
  };
  try {
    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/automatizaciones/${id}` : '/api/automatizaciones';
    const r = await API._fetch(url, { method, headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    if (!r.ok) { const e = await r.json(); toast(e.detail || 'Error al guardar'); return; }
    toast(id ? 'Automatización actualizada' : 'Automatización creada');
    closeModal();
    loadAutomatizaciones();
    loadHomeDashboard();
  } catch(e) { toast('Error de red'); }
}

async function deleteAuto(id, nombre) {
  if (!confirm(`¿Eliminar la automatización "${nombre}"?`)) return;
  try {
    const r = await API._fetch(`/api/automatizaciones/${id}`, { method: 'DELETE' });
    if (r.ok || r.status === 204) {
      toast('Automatización eliminada');
      loadAutomatizaciones();
      loadHomeDashboard();
    } else { toast('Error al eliminar'); }
  } catch(e) { toast('Error de red'); }
}

// ── KPIs ─────────────────────────────────────────────────────
async function loadKpis() {
  const container = document.getElementById('kpisList');
  if (!container) return;
  container.innerHTML = '<div class="loading-row"><div class="spinner"></div></div>';
  try {
    const r = await API._fetch('/api/kpis');
    _kpis = r.ok ? await r.json() : [];
    renderKpis();
  } catch(e) {
    container.innerHTML = '<div class="empty-state"><p>Error cargando KPIs.</p></div>';
  }
}

function renderKpis() {
  const container = document.getElementById('kpisList');
  if (!container) return;
  if (_kpis.length === 0) {
    container.innerHTML = emptyState(ICON_KPI, 'Sin KPIs', 'Añade indicadores de rendimiento para hacer seguimiento de la evolución de tu empresa.');
    return;
  }
  const tendIcon = t => t === 'up' ? '↑' : t === 'down' ? '↓' : '→';
  const tendCol  = t => t === 'up' ? 'var(--emerald)' : t === 'down' ? 'var(--rose)' : 'var(--amber)';
  container.innerHTML = `<div class="cards-grid">
    ${_kpis.map(k => `
      <div class="card-item">
        <div class="card-item-header">
          <div>
            <div class="card-item-title">${escHtml(k.nombre)}</div>
            ${k.categoria ? `<div class="card-item-sub">${escHtml(k.categoria)}</div>` : ''}
          </div>
          <span style="font-size:1.4rem;font-weight:700;color:${tendCol(k.tendencia)}">${tendIcon(k.tendencia)}</span>
        </div>
        <div style="font-size:1.6rem;font-weight:700;color:var(--fg);margin:.4rem 0">${escHtml(k.valor)}${k.unidad ? `<span style="font-size:.85rem;font-weight:400;color:var(--fg-3);margin-left:.3rem">${escHtml(k.unidad)}</span>` : ''}</div>
        ${k.objetivo ? `<div style="font-size:.72rem;color:var(--fg-3)">Objetivo: ${escHtml(k.objetivo)}</div>` : ''}
        <div class="card-item-actions">
          <button class="icon-action" title="Editar" onclick="openKpiModal(${JSON.stringify(k).replace(/"/g,'&quot;')})">${ICON_EDIT}</button>
          <button class="icon-action danger" title="Eliminar" onclick="deleteKpi('${k.id}','${escHtml(k.nombre)}')">${ICON_TRASH}</button>
        </div>
      </div>`).join('')}
  </div>`;
}

function openKpiModal(data) {
  const isEdit = data && data.id;
  const body = `
    <div class="form-grid">
      <div class="field-group" style="grid-column:1/-1">
        <label class="field-label">Nombre del KPI *</label>
        <input class="field-input" id="kNombre" value="${escHtml(isEdit ? data.nombre : '')}" placeholder="Ej: Tiempo de resolución"/>
      </div>
      <div class="field-group">
        <label class="field-label">Valor actual *</label>
        <input class="field-input" id="kValor" value="${escHtml(isEdit ? data.valor : '')}" placeholder="Ej: 2.8"/>
      </div>
      <div class="field-group">
        <label class="field-label">Unidad</label>
        <input class="field-input" id="kUnidad" value="${escHtml(isEdit ? (data.unidad||'') : '')}" placeholder="días, %, €…"/>
      </div>
      <div class="field-group">
        <label class="field-label">Objetivo</label>
        <input class="field-input" id="kObj" value="${escHtml(isEdit ? (data.objetivo||'') : '')}" placeholder="Ej: 2 días"/>
      </div>
      <div class="field-group">
        <label class="field-label">Categoría</label>
        <select class="field-select" id="kCat">
          <option value="">— Sin categoría —</option>
          ${['tiempo','coste','calidad','volumen'].map(c =>
            `<option value="${c}" ${isEdit && data.categoria === c ? 'selected' : ''}>${c.charAt(0).toUpperCase()+c.slice(1)}</option>`
          ).join('')}
        </select>
      </div>
      <div class="field-group">
        <label class="field-label">Tendencia</label>
        <select class="field-select" id="kTend">
          ${[['up','↑ Subiendo'],['down','↓ Bajando'],['flat','→ Estable']].map(([v,l]) =>
            `<option value="${v}" ${isEdit && data.tendencia === v ? 'selected' : ''}>${l}</option>`
          ).join('')}
        </select>
      </div>
    </div>`;
  const foot = `<button class="btn-secondary" onclick="closeModal()">Cancelar</button>
    <button class="btn-cta" onclick="saveKpi(${isEdit ? `'${data.id}'` : 'null'})">${isEdit ? 'Guardar cambios' : 'Crear KPI'}</button>`;
  openModal('custom', isEdit ? 'Editar KPI' : 'Nuevo KPI', body, foot);
}

async function saveKpi(id) {
  const nombre = document.getElementById('kNombre').value.trim();
  const valor  = document.getElementById('kValor').value.trim();
  if (!nombre || !valor) { toast('Nombre y valor son obligatorios'); return; }
  const payload = {
    nombre, valor,
    unidad:    document.getElementById('kUnidad').value.trim() || null,
    objetivo:  document.getElementById('kObj').value.trim() || null,
    categoria: document.getElementById('kCat').value || null,
    tendencia: document.getElementById('kTend').value,
  };
  try {
    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/kpis/${id}` : '/api/kpis';
    const r = await API._fetch(url, { method, headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    if (!r.ok) { const e = await r.json(); toast(e.detail || 'Error al guardar'); return; }
    toast(id ? 'KPI actualizado' : 'KPI creado');
    closeModal();
    loadKpis();
    loadHomeDashboard();
  } catch(e) { toast('Error de red'); }
}

async function deleteKpi(id, nombre) {
  if (!confirm(`¿Eliminar el KPI "${nombre}"?`)) return;
  try {
    const r = await API._fetch(`/api/kpis/${id}`, { method: 'DELETE' });
    if (r.ok || r.status === 204) {
      toast('KPI eliminado');
      loadKpis();
      loadHomeDashboard();
    } else { toast('Error al eliminar'); }
  } catch(e) { toast('Error de red'); }
}

// ── PROPUESTAS (conversaciones del agente) ────────────────────
async function loadPropuestas() {
  const container = document.getElementById('propuestasList');
  if (!container) return;
  container.innerHTML = '<div class="loading-row"><div class="spinner"></div></div>';
  try {
    const r = await API._fetch('/api/agente/conversaciones');
    const convs = r.ok ? await r.json() : [];
    if (convs.length === 0) {
      container.innerHTML = emptyState(
        `<svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
        'Sin conversaciones',
        'Las conversaciones con el agente IA aparecerán aquí con sus propuestas y análisis.'
      );
      return;
    }
    container.innerHTML = `<div class="cards-grid">
      ${convs.map(c => {
        const msgs = (() => { try { return JSON.parse(c.historial||'[]'); } catch(e) { return []; } })();
        const lastMsg = msgs.filter(m => m.role === 'assistant').pop();
        const date = c.updated_at ? new Date(c.updated_at).toLocaleDateString('es-ES') : '';
        return `<div class="card-item">
          <div class="card-item-header">
            <div>
              <div class="card-item-title">${escHtml(c.titulo || 'Conversación')}</div>
              <div class="card-item-sub">${msgs.length} mensaje${msgs.length !== 1 ? 's' : ''} · ${escHtml(date)}</div>
            </div>
            <span class="status-pill pending"><span class="status-dot"></span>${escHtml(c.fase || 'diagnostico')}</span>
          </div>
          ${lastMsg ? `<p style="font-size:.78rem;color:var(--fg-2);line-height:1.5;margin:.5rem 0">${escHtml(lastMsg.content.substring(0,150))}${lastMsg.content.length>150?'…':''}</p>` : ''}
          <div class="card-item-actions">
            <button class="btn-secondary" style="font-size:.72rem;padding:.3rem .6rem" onclick="abrirConversacion('${c.id}')">Continuar →</button>
            <button class="icon-action danger" title="Eliminar" onclick="deleteConversacion('${c.id}')">${ICON_TRASH}</button>
          </div>
        </div>`;
      }).join('')}
    </div>`;
  } catch(e) {
    container.innerHTML = '<div class="empty-state"><p>Error cargando propuestas.</p></div>';
  }
}

function abrirConversacion(convId) {
  _conversacionId = convId;
  setPage(document.querySelector('[data-page="Agente IA"]'), 'Agente IA', 'page-agente');
}

async function deleteConversacion(id) {
  if (!confirm('¿Eliminar esta conversación?')) return;
  try {
    const r = await API._fetch(`/api/agente/conversaciones/${id}`, { method: 'DELETE' });
    if (r.ok || r.status === 204) { toast('Conversación eliminada'); loadPropuestas(); }
    else { toast('Error al eliminar'); }
  } catch(e) { toast('Error de red'); }
}

// ── AGENTE IA CHAT ────────────────────────────────────────────
function nuevaConversacion() {
  _conversacionId = null;
  const msgs = document.getElementById('chatMessages');
  if (msgs) msgs.innerHTML = `<div class="msg-full agent">
    <div class="msg-avatar">B</div>
    <div class="msg-text">¡Nueva conversación iniciada! ¿En qué puedo ayudarte hoy?</div>
  </div>`;
  const input = document.getElementById('chatInput');
  if (input) { input.value = ''; input.focus(); }
}

async function sendChat() {
  const input = document.getElementById('chatInput');
  if (!input || !input.value.trim()) return;
  const mensaje = input.value.trim();
  input.value = '';

  const msgs = document.getElementById('chatMessages');
  const user = API.session.get();

  // Add user message
  const userInitials = user ? ((user.nombre||'U')[0] + (user.apellido||'U')[0]).toUpperCase() : 'U';
  appendMsg(msgs, 'user', userInitials, mensaje);

  // Typing indicator
  const typingId = 'typing_' + Date.now();
  msgs.innerHTML += `<div class="msg-full agent" id="${typingId}">
    <div class="msg-avatar">B</div>
    <div class="msg-text"><div class="chat-typing"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div></div>
  </div>`;
  msgs.scrollTop = msgs.scrollHeight;

  // Disable send
  const btn = document.getElementById('chatSendBtn');
  if (btn) btn.disabled = true;

  try {
    const r = await API._fetch('/api/agente/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mensaje, conversacion_id: _conversacionId }),
    });

    // Remove typing
    const typingEl = document.getElementById(typingId);
    if (typingEl) typingEl.remove();

    if (r.ok) {
      const data = await r.json();
      _conversacionId = data.conversacion_id;
      appendMsg(msgs, 'agent', 'B', data.respuesta);
    } else {
      appendMsg(msgs, 'agent', 'B', 'Hubo un error al procesar tu mensaje. Verifica que el servidor esté corriendo.');
    }
  } catch(e) {
    const typingEl = document.getElementById(typingId);
    if (typingEl) typingEl.remove();
    appendMsg(msgs, 'agent', 'B', 'No se pudo conectar con el agente. Verifica que el backend esté activo en http://localhost:8001');
  }

  if (btn) btn.disabled = false;
  msgs.scrollTop = msgs.scrollHeight;
}

function appendMsg(container, role, avatar, text) {
  const div = document.createElement('div');
  div.className = `msg-full ${role}`;
  div.innerHTML = `<div class="msg-avatar">${escHtml(avatar)}</div>
    <div class="msg-text">${escHtml(text).replace(/\n/g,'<br>')}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

// Quick chat from home panel
async function homeQuickChat() {
  const input = document.getElementById('homeChatInput');
  if (!input || !input.value.trim()) return;
  const msg = input.value.trim();
  input.value = '';
  // Switch to agente page and send
  setPage(document.querySelector('[data-page="Agente IA"]'), 'Agente IA', 'page-agente');
  setTimeout(() => {
    const chatInput = document.getElementById('chatInput');
    if (chatInput) { chatInput.value = msg; sendChat(); }
  }, 100);
}

// ── Extend openModal for custom content ───────────────────────
// The original openModal only has predefined cases.
// We monkey-patch it to support 'custom'.
const _origOpenModal = window.openModal;
window.openModal = function(type, title, body, foot) {
  if (type === 'custom') {
    const titleEl = document.getElementById('modalTitle');
    const bodyEl  = document.getElementById('modalBody');
    const footEl  = document.getElementById('modalFoot');
    const back    = document.getElementById('modalBackdrop');
    if (titleEl) titleEl.textContent = title;
    if (bodyEl)  bodyEl.innerHTML = body;
    if (footEl)  footEl.innerHTML = foot || '';
    if (back)    back.classList.add('show');
    return;
  }
  if (_origOpenModal) _origOpenModal(type);
};

// ── Patch API to expose _fetch ────────────────────────────────
// api.js uses _apiFetch internally but doesn't expose it.
// We add a thin wrapper that uses the stored token.
API._fetch = function(path, opts = {}) {
  const token = sessionStorage.getItem('bpa_token');
  const headers = { ...(opts.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return fetch('http://localhost:8001' + path, { ...opts, headers });
};
