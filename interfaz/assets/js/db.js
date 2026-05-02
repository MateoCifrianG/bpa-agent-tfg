/**
 * BPA-Agent · DB simulada en localStorage
 * Roles: admin | user
 */

const DB_KEY   = 'bpa_db';
const SESS_KEY = 'bpa_session';

// ── Seed inicial ─────────────────────────────────────────────────────────
const SEED = {
  users: [
    {
      id: 'u-admin',
      email: 'admin@bpa.com',
      password: 'Admin1234!',
      role: 'admin',
      nombre: 'Mateo',
      apellido: 'Cifrián',
      empresa: 'BPA-Agent',
      sector: 'Tecnología',
      empleados: 1,
      plan: 'enterprise',
      avatar: 'MC',
      telefono: '+34 600 000 001',
      ciudad: 'Bilbao',
      activo: true,
      createdAt: '2026-01-01T00:00:00Z',
      stats: { procesos: 0, automatizaciones: 0, horasAhorradas: 0, score: 100 },
      procesos: [],
      automatizaciones: [],
      kpis: []
    },
    {
      id: 'u-1',
      email: 'ana.garcia@eroskidigital.com',
      password: 'Eroski2026!',
      role: 'user',
      nombre: 'Ana',
      apellido: 'García Uriarte',
      empresa: 'Eroski Digital',
      sector: 'Retail',
      empleados: 340,
      plan: 'pro',
      avatar: 'AG',
      telefono: '+34 946 211 200',
      ciudad: 'Elorrio',
      activo: true,
      createdAt: '2026-02-03T09:15:00Z',
      stats: { procesos: 11, automatizaciones: 6, horasAhorradas: 87, score: 74 },
      procesos: [
        { nombre: 'Gestión de devoluciones', score: 41, estado: 'analizado' },
        { nombre: 'Alta de proveedor', score: 58, estado: 'analizado' },
        { nombre: 'Generación de informes semanales', score: 33, estado: 'critico' },
        { nombre: 'Seguimiento de incidencias logísticas', score: 67, estado: 'analizado' },
        { nombre: 'Control de stock mínimo', score: 80, estado: 'optimizado' }
      ],
      automatizaciones: [
        { nombre: 'Notificación automática devolución cliente', herramienta: 'Gmail', estado: 'activa', ejecuciones: 203 },
        { nombre: 'Reporte diario de stock a Drive', herramienta: 'Drive', estado: 'activa', ejecuciones: 41 },
        { nombre: 'Alta proveedor en ERP vía formulario', herramienta: 'n8n', estado: 'pendiente', ejecuciones: 0 }
      ],
      kpis: [
        { nombre: 'Tiempo medio resolución devolución', valor: '2.1 días', objetivo: '1 día', tendencia: 'down' },
        { nombre: 'Incidencias logísticas/semana', valor: 14, objetivo: 5, tendencia: 'down' },
        { nombre: 'Coste operativo mensual automatizado', valor: '1.240 €', objetivo: '800 €', tendencia: 'up' }
      ]
    },
    {
      id: 'u-2',
      email: 'jon.etxeberria@mondragon.edu',
      password: 'Mondragon2026!',
      role: 'user',
      nombre: 'Jon',
      apellido: 'Etxeberria Arrate',
      empresa: 'Mondragon Unibertsitatea',
      sector: 'Educación',
      empleados: 620,
      plan: 'pro',
      avatar: 'JE',
      telefono: '+34 943 794 700',
      ciudad: 'Mondragón',
      activo: true,
      createdAt: '2026-02-17T10:00:00Z',
      stats: { procesos: 9, automatizaciones: 5, horasAhorradas: 112, score: 82 },
      procesos: [
        { nombre: 'Matriculación de alumnos nuevo curso', score: 55, estado: 'analizado' },
        { nombre: 'Generación de certificados académicos', score: 38, estado: 'critico' },
        { nombre: 'Seguimiento de TFGs en curso', score: 71, estado: 'analizado' },
        { nombre: 'Comunicación con empresas colaboradoras', score: 44, estado: 'analizado' },
        { nombre: 'Planificación horaria semestral', score: 62, estado: 'analizado' }
      ],
      automatizaciones: [
        { nombre: 'Envío automático certificado PDF por email', herramienta: 'Gmail + Drive', estado: 'activa', ejecuciones: 318 },
        { nombre: 'Recordatorio TFG a tutores cada 2 semanas', herramienta: 'Calendar', estado: 'activa', ejecuciones: 28 },
        { nombre: 'Actualización estado matrícula en Sheets', herramienta: 'Sheets', estado: 'activa', ejecuciones: 89 }
      ],
      kpis: [
        { nombre: 'Tiempo emisión certificado académico', valor: '4 h', objetivo: '15 min', tendencia: 'up' },
        { nombre: 'TFGs entregados a tiempo', valor: '71%', objetivo: '90%', tendencia: 'up' },
        { nombre: 'Horas admin ahorradas/mes', valor: 112, objetivo: 150, tendencia: 'up' }
      ]
    },
    {
      id: 'u-3',
      email: 'marta.lopez@gasnaturalsdg.es',
      password: 'GasNatural26!',
      role: 'user',
      nombre: 'Marta',
      apellido: 'López Sánchez',
      empresa: 'Gas Natural SDG',
      sector: 'Energía',
      empleados: 1200,
      plan: 'enterprise',
      avatar: 'ML',
      telefono: '+34 900 100 212',
      ciudad: 'Barcelona',
      activo: true,
      createdAt: '2026-03-05T08:30:00Z',
      stats: { procesos: 18, automatizaciones: 11, horasAhorradas: 240, score: 89 },
      procesos: [
        { nombre: 'Alta de nuevo punto de suministro', score: 72, estado: 'analizado' },
        { nombre: 'Gestión de reclamaciones tarifarias', score: 49, estado: 'analizado' },
        { nombre: 'Inspección técnica y registro de incidencias', score: 61, estado: 'analizado' },
        { nombre: 'Facturación mensual a grandes cuentas', score: 84, estado: 'optimizado' },
        { nombre: 'Renovación de contratos de mantenimiento', score: 53, estado: 'analizado' }
      ],
      automatizaciones: [
        { nombre: 'Apertura ticket reclamación desde email cliente', herramienta: 'Gmail + n8n', estado: 'activa', ejecuciones: 512 },
        { nombre: 'Generación y envío factura PDF mensual', herramienta: 'Drive + Gmail', estado: 'activa', ejecuciones: 1200 },
        { nombre: 'Alerta inspector cuando incidencia es crítica', herramienta: 'n8n + Calendar', estado: 'activa', ejecuciones: 34 }
      ],
      kpis: [
        { nombre: 'Tiempo resolución reclamación', valor: '3.4 días', objetivo: '1 día', tendencia: 'up' },
        { nombre: 'Contratos renovados sin intervención manual', valor: '68%', objetivo: '95%', tendencia: 'up' },
        { nombre: 'Coste gestión por contrato/mes', valor: '4.20 €', objetivo: '1.50 €', tendencia: 'up' }
      ]
    },
    {
      id: 'u-4',
      email: 'pablo.fernandez@ikea.es',
      password: 'Ikea2026!',
      role: 'user',
      nombre: 'Pablo',
      apellido: 'Fernández Mora',
      empresa: 'IKEA España',
      sector: 'Retail',
      empleados: 7800,
      plan: 'pro',
      avatar: 'PF',
      telefono: '+34 900 400 500',
      ciudad: 'Madrid',
      activo: true,
      createdAt: '2026-03-18T11:00:00Z',
      stats: { procesos: 13, automatizaciones: 7, horasAhorradas: 156, score: 77 },
      procesos: [
        { nombre: 'Onboarding empleado nuevo', score: 43, estado: 'critico' },
        { nombre: 'Gestión de ausencias y sustituciones', score: 60, estado: 'analizado' },
        { nombre: 'Cierre de caja y conciliación diaria', score: 75, estado: 'analizado' },
        { nombre: 'Solicitud y aprobación de vacaciones', score: 55, estado: 'analizado' },
        { nombre: 'Formación obligatoria PRL', score: 38, estado: 'critico' }
      ],
      automatizaciones: [
        { nombre: 'Email bienvenida + accesos empleado nuevo', herramienta: 'Gmail + Drive', estado: 'activa', ejecuciones: 47 },
        { nombre: 'Recordatorio formación PRL vencida', herramienta: 'Calendar + Gmail', estado: 'activa', ejecuciones: 93 },
        { nombre: 'Informe cierre caja a manager', herramienta: 'Sheets', estado: 'pendiente', ejecuciones: 0 }
      ],
      kpis: [
        { nombre: 'Tiempo onboarding completo', valor: '8 días', objetivo: '2 días', tendencia: 'up' },
        { nombre: 'Empleados con PRL al día', valor: '64%', objetivo: '100%', tendencia: 'up' },
        { nombre: 'Horas RRHH ahorradas/mes', valor: 156, objetivo: 200, tendencia: 'up' }
      ]
    },
    {
      id: 'u-5',
      email: 'lucia.navarro@clinicanavarro.es',
      password: 'Clinica2026!',
      role: 'user',
      nombre: 'Lucía',
      apellido: 'Navarro Ibáñez',
      empresa: 'Clínica Navarro',
      sector: 'Salud',
      empleados: 38,
      plan: 'free',
      avatar: 'LN',
      telefono: '+34 963 211 800',
      ciudad: 'Valencia',
      activo: true,
      createdAt: '2026-04-08T09:00:00Z',
      stats: { procesos: 5, automatizaciones: 2, horasAhorradas: 31, score: 58 },
      procesos: [
        { nombre: 'Recordatorio cita a pacientes', score: 36, estado: 'critico' },
        { nombre: 'Envío resultados analíticas', score: 50, estado: 'analizado' },
        { nombre: 'Gestión lista de espera', score: 44, estado: 'analizado' },
        { nombre: 'Facturación a mutuas', score: 62, estado: 'analizado' },
        { nombre: 'Alta de nuevo paciente', score: 55, estado: 'analizado' }
      ],
      automatizaciones: [
        { nombre: 'SMS recordatorio cita 24h antes', herramienta: 'n8n', estado: 'activa', ejecuciones: 287 },
        { nombre: 'Email resultados analítica cuando disponible', herramienta: 'Gmail', estado: 'pendiente', ejecuciones: 0 }
      ],
      kpis: [
        { nombre: 'Tasa no-show citas', valor: '22%', objetivo: '5%', tendencia: 'down' },
        { nombre: 'Tiempo envío resultados', valor: '3.1 días', objetivo: '4 h', tendencia: 'down' },
        { nombre: 'Pacientes gestionados/semana', valor: 89, objetivo: 120, tendencia: 'up' }
      ]
    }
  ]
};

// ── Init ─────────────────────────────────────────────────────────────────
function _getDB() {
  const raw = localStorage.getItem(DB_KEY);
  if (!raw) {
    localStorage.setItem(DB_KEY, JSON.stringify(SEED));
    return SEED;
  }
  return JSON.parse(raw);
}

function _saveDB(db) {
  localStorage.setItem(DB_KEY, JSON.stringify(db));
}

// ── Auth ─────────────────────────────────────────────────────────────────
const Auth = {
  login(email, password) {
    const db   = _getDB();
    const user = db.users.find(u => u.email.toLowerCase() === email.toLowerCase() && u.password === password);
    if (!user) return { ok: false, error: 'Credenciales incorrectas.' };
    if (!user.activo) return { ok: false, error: 'Cuenta desactivada. Contacta con soporte.' };
    const session = { userId: user.id, role: user.role, loginAt: new Date().toISOString() };
    sessionStorage.setItem(SESS_KEY, JSON.stringify(session));
    return { ok: true, user, role: user.role };
  },

  logout() {
    sessionStorage.removeItem(SESS_KEY);
    window.location.href = 'login.html';
  },

  session() {
    const raw = sessionStorage.getItem(SESS_KEY);
    return raw ? JSON.parse(raw) : null;
  },

  currentUser() {
    const sess = this.session();
    if (!sess) return null;
    return Users.getById(sess.userId);
  },

  // Redirige a login si no hay sesión; si requiere rol lo comprueba
  guard(requiredRole) {
    const sess = this.session();
    if (!sess) { window.location.href = 'login.html'; return null; }
    if (requiredRole && sess.role !== requiredRole) {
      window.location.href = sess.role === 'admin' ? 'admin.html' : 'dashboard.html';
      return null;
    }
    return sess;
  }
};

// ── Users CRUD ────────────────────────────────────────────────────────────
const Users = {
  all() { return _getDB().users; },

  getById(id) { return _getDB().users.find(u => u.id === id) || null; },

  getByEmail(email) { return _getDB().users.find(u => u.email.toLowerCase() === email.toLowerCase()) || null; },

  create(data) {
    const db = _getDB();
    if (db.users.find(u => u.email.toLowerCase() === data.email.toLowerCase())) {
      return { ok: false, error: 'Ya existe una cuenta con ese correo.' };
    }
    const user = {
      id: 'u-' + Date.now(),
      email: data.email,
      password: data.password,
      role: 'user',
      nombre: data.nombre || '',
      apellido: data.apellido || '',
      empresa: data.empresa || '',
      sector: data.sector || '',
      empleados: data.empleados || 0,
      plan: data.plan || 'free',
      avatar: ((data.nombre || 'U')[0] + (data.apellido || 'U')[0]).toUpperCase(),
      activo: true,
      createdAt: new Date().toISOString(),
      stats: { procesos: 0, automatizaciones: 0, horasAhorradas: 0, score: 0 }
    };
    db.users.push(user);
    _saveDB(db);
    return { ok: true, user };
  },

  update(id, changes) {
    const db   = _getDB();
    const idx  = db.users.findIndex(u => u.id === id);
    if (idx === -1) return { ok: false, error: 'Usuario no encontrado.' };
    db.users[idx] = { ...db.users[idx], ...changes };
    if (changes.nombre || changes.apellido) {
      const u = db.users[idx];
      db.users[idx].avatar = ((u.nombre || 'U')[0] + (u.apellido || 'U')[0]).toUpperCase();
    }
    _saveDB(db);
    return { ok: true, user: db.users[idx] };
  },

  changePassword(id, current, next) {
    const db  = _getDB();
    const idx = db.users.findIndex(u => u.id === id);
    if (idx === -1) return { ok: false, error: 'Usuario no encontrado.' };
    if (db.users[idx].password !== current) return { ok: false, error: 'Contraseña actual incorrecta.' };
    db.users[idx].password = next;
    _saveDB(db);
    return { ok: true };
  },

  toggleActive(id) {
    const u = this.getById(id);
    if (!u) return;
    return this.update(id, { activo: !u.activo });
  },

  delete(id) {
    const db  = _getDB();
    db.users  = db.users.filter(u => u.id !== id);
    _saveDB(db);
  },

  // Estadísticas globales para admin
  globalStats() {
    const users   = this.all().filter(u => u.role !== 'admin');
    const activos = users.filter(u => u.activo).length;
    const pro     = users.filter(u => u.plan === 'pro').length;
    const total_procesos       = users.reduce((s,u) => s + u.stats.procesos, 0);
    const total_automatizaciones = users.reduce((s,u) => s + u.stats.automatizaciones, 0);
    const total_horas          = users.reduce((s,u) => s + u.stats.horasAhorradas, 0);
    const avg_score            = users.length ? Math.round(users.reduce((s,u) => s + u.stats.score, 0) / users.length) : 0;
    return { total: users.length, activos, inactivos: users.length - activos, pro, free: users.length - pro,
             total_procesos, total_automatizaciones, total_horas, avg_score };
  }
};

// ── Reset (útil para desarrollo) ─────────────────────────────────────────
function resetDB() { localStorage.removeItem(DB_KEY); _getDB(); console.log('DB reseteada.'); }
