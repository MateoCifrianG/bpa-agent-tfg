/**
 * BPA-Agent · API client
 * Conecta la interfaz HTML con el backend FastAPI en localhost:8002
 */

const API_BASE = 'http://localhost:8002';

// ── Sesión (sessionStorage para persistir entre páginas) ─────────────────
const _session = {
  accessToken: null,
  user: null,

  set(token, user, refreshToken) {
    this.accessToken = token;
    this.user = user;
    sessionStorage.setItem('bpa_token', token);
    sessionStorage.setItem('bpa_user', JSON.stringify(user));
    if (refreshToken) sessionStorage.setItem('bpa_refresh', refreshToken);
  },

  get() {
    if (!this.accessToken) {
      this.accessToken = sessionStorage.getItem('bpa_token');
      const raw = sessionStorage.getItem('bpa_user');
      try { this.user = raw ? JSON.parse(raw) : null; } catch { this.user = null; }
    }
    return { token: this.accessToken, user: this.user };
  },

  getRefresh() { return sessionStorage.getItem('bpa_refresh'); },

  clear() {
    this.accessToken = null;
    this.user = null;
    sessionStorage.removeItem('bpa_token');
    sessionStorage.removeItem('bpa_user');
    sessionStorage.removeItem('bpa_refresh');
  },

  isAuth() {
    return !!this.get().token;
  }
};

// ── Helper fetch con manejo robusto de errores ───────────────────────────
let _refreshing = null; // singleton promise para evitar múltiples refresh simultáneos

async function _tryRefresh() {
  if (_refreshing) return _refreshing;
  _refreshing = (async () => {
    try {
      const storedRefresh = _session.getRefresh();
      const res = await fetch(`${API_BASE}/api/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        // enviar también por body para que funcione desde file://
        body: storedRefresh ? JSON.stringify({ refresh_token: storedRefresh }) : '{}',
      });
      if (!res.ok) return false;
      const data = await res.json().catch(() => null);
      if (data?.access_token) {
        _session.set(data.access_token, data.user || _session.get().user, storedRefresh);
        return true;
      }
      return false;
    } catch { return false; }
    finally { _refreshing = null; }
  })();
  return _refreshing;
}

async function _apiFetch(path, options = {}, _retry = false) {
  const { token } = _session.get();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  let res, data;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
      credentials: 'include',
    });
    data = await res.json().catch(() => ({}));
  } catch (networkErr) {
    console.error('[BPA API] Error de red:', networkErr);
    return {
      ok: false,
      error: 'No se pudo conectar con el servidor. ¿Está el backend corriendo en el puerto 8002?',
    };
  }

  // Token expirado → intentar refresh una sola vez
  if (res.status === 401 && !_retry && path !== '/api/auth/refresh') {
    const refreshed = await _tryRefresh();
    if (refreshed) return _apiFetch(path, options, true);
    // Refresh falló → redirigir a login
    _session.clear();
    window.location.href = 'login.html';
    return { ok: false, error: 'Sesión expirada' };
  }

  if (!res.ok) {
    const msg = data.detail || 'Error inesperado del servidor.';
    return { ok: false, error: typeof msg === 'string' ? msg : JSON.stringify(msg) };
  }

  return { ok: true, data };
}

// ── Auth API ─────────────────────────────────────────────────────────────
const API = {

  async login(email, password) {
    const result = await _apiFetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (!result.ok) return result;
    const { access_token, refresh_token, user } = result.data;
    _session.set(access_token, user, refresh_token);
    return { ok: true, user, role: user.role };
  },

  async register({ nombre, apellido, empresa, email, password, plan }) {
    const result = await _apiFetch('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        nombre:    nombre    || '',
        apellido:  apellido  || '',
        empresa:   empresa   || '',
        email,
        password,
        plan:      plan      || 'free',
        sector:    'General',
        empleados: 1,
      }),
    });
    if (!result.ok) return result;
    const { access_token, refresh_token, user } = result.data;
    _session.set(access_token, user, refresh_token);
    return { ok: true, user, role: user.role };
  },

  async me() {
    return await _apiFetch('/api/auth/me');
  },

  async logout() {
    try { await _apiFetch('/api/auth/logout', { method: 'POST' }); } catch (_) {}
    _session.clear();
    window.location.href = 'login.html';
  },

  session: _session,

  // Guard: redirige a login si no hay sesión; comprueba rol si se indica
  guard(requiredRole) {
    const { token, user } = _session.get();
    if (!token || !user) {
      window.location.href = 'login.html';
      return null;
    }
    if (requiredRole && user.role !== requiredRole) {
      window.location.href = user.role === 'admin' ? 'admin.html' : 'dashboard.html';
      return null;
    }
    return user;
  },

  // Inyectar datos del usuario en los elementos estándar del layout
  injectUser() {
    const { user } = _session.get();
    if (!user) return;
    const initials = ((user.nombre || 'U')[0] + (user.apellido || 'U')[0]).toUpperCase();
    const fullName = [user.nombre, user.apellido].filter(Boolean).join(' ') || user.email;
    const planLabel = { free: 'Plan Gratuito', pro: 'Plan Pro', enterprise: 'Enterprise' }[user.plan] || 'Plan Gratuito';

    document.querySelectorAll('.avatar, .dd-avatar').forEach(el => el.textContent = initials);
    document.querySelectorAll('.user-name, .dd-name').forEach(el => el.textContent = fullName);
    document.querySelectorAll('.user-plan').forEach(el => el.textContent = planLabel);
    document.querySelectorAll('.dd-email, .user-email').forEach(el => el.textContent = user.email);
    return user;
  },
};
