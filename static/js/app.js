/**
 * BuszApp – Shared Utilities
 * Common helpers used across all pages
 */

// ── API Client ────────────────────────────────────────────────────────────────

const API = {
  async request(method, path, body = null) {
    const opts = {
      method,
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw Object.assign(new Error(data.error || 'Erro na requisição'), { status: res.status, data });
    return data;
  },
  get:    (path)        => API.request('GET', path),
  post:   (path, body)  => API.request('POST', path, body),
  put:    (path, body)  => API.request('PUT', path, body),
  delete: (path)        => API.request('DELETE', path),
};

// ── Toast Notifications ───────────────────────────────────────────────────────

const Toast = (() => {
  let container;

  function getContainer() {
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    return container;
  }

  const FEATHER_ICON = {
    success: 'check-circle',
    error:   'alert-circle',
    warning: 'alert-triangle',
    info:    'info',
  };

  function show(message, type = 'info', duration = 4000) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <i data-feather="${FEATHER_ICON[type] || FEATHER_ICON.info}" class="toast-icon"></i>
      <span class="toast-message">${escapeHtml(message)}</span>
      <button type="button" class="toast-dismiss" aria-label="Fechar">
        <i data-feather="x" class="w-4 h-4"></i>
      </button>
    `;
    toast.querySelector('.toast-dismiss').addEventListener('click', () => toast.remove());
    getContainer().appendChild(toast);
    if (typeof window.feather !== 'undefined') window.feather.replace();
    if (duration > 0) setTimeout(() => toast.remove(), duration);
    return toast;
  }

  return {
    success: (msg, d) => show(msg, 'success', d),
    error:   (msg, d) => show(msg, 'error', d),
    warning: (msg, d) => show(msg, 'warning', d),
    info:    (msg, d) => show(msg, 'info', d),
  };
})();

// ── Auth Helpers ──────────────────────────────────────────────────────────────

async function checkAuth(redirectIfGuest = true) {
  try {
    const user = await API.get('/api/auth/profile');
    return user;
  } catch {
    if (redirectIfGuest) window.location.href = '/login';
    return null;
  }
}

async function requireAdmin() {
  const user = await checkAuth(true);
  if (user && user.role !== 'admin') {
    Toast.error('Acesso restrito a administradores.');
    setTimeout(() => window.location.href = '/dashboard', 1500);
    return null;
  }
  return user;
}

async function logout() {
  await API.post('/api/auth/logout').catch(() => {});
  localStorage.removeItem('buszapp_user_id');
  localStorage.removeItem('driver_id');
  window.location.href = '/login';
}

// ── Dark Mode ─────────────────────────────────────────────────────────────────

const DarkMode = {
  init() {
    const saved = localStorage.getItem('theme');
    if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      document.documentElement.classList.add('dark');
    }
  },
  toggle() {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  },
  isDark: () => document.documentElement.classList.contains('dark'),
};

// ── Sidebar ───────────────────────────────────────────────────────────────────

const Sidebar = {
  init() {
    const noSidebar = ['', 'index', 'login', 'register', 'forgot-password', 'terms'];
    const page = (window.location.pathname.split('/').pop() || '').replace(/\.html$/, '');
    if (noSidebar.includes(page)) return;

    let sidebar = document.getElementById('sidebar');
    let overlay = document.getElementById('sidebarOverlay');
    let toggle  = document.getElementById('menuToggle');

    // Auto-inject sidebar if page doesn't have one
    if (!sidebar) {
      sidebar = document.createElement('nav');
      sidebar.id = 'sidebar';
      sidebar.className = 'sidebar flex flex-col pb-4';
      sidebar.setAttribute('aria-label', 'Navegação principal');
      document.body.insertAdjacentElement('afterbegin', sidebar);
    }
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'sidebarOverlay';
      overlay.className = 'sidebar-overlay';
      document.body.insertAdjacentElement('afterbegin', overlay);
    }
    if (!toggle) {
      toggle = document.createElement('button');
      toggle.id = 'menuToggle';
      toggle.className = 'menu-toggle';
      toggle.setAttribute('aria-label', 'Menu');
      toggle.innerHTML = '<i data-feather="menu" class="w-6 h-6"></i>';
      document.body.insertAdjacentElement('afterbegin', toggle);
    }

    // Standardize sidebar content across all pages
    sidebar.innerHTML = `
      <a href="/dashboard" id="sidebarHome" class="sidebar-item gap-3 hidden">
        <i data-feather="home"></i><span>Início</span>
      </a>
      <a href="/admin" id="sidebarAdmin" class="sidebar-item gap-3 hidden">
        <i data-feather="layout"></i><span>Painel Admin</span>
      </a>
      <a href="/add-driver" id="sidebarDrivers" class="sidebar-item gap-3 hidden">
        <i data-feather="users"></i><span>Motoristas</span>
      </a>
      <a href="/add-vehicle" id="sidebarFleet" class="sidebar-item gap-3 hidden">
        <i data-feather="truck"></i><span>Frota</span>
      </a>
      <a href="/admin-rotas" id="sidebarRoutes" class="sidebar-item gap-3 hidden">
        <i data-feather="map"></i><span>Rotas</span>
      </a>
      <a href="/acompanhamento" id="sidebarTrack" class="sidebar-item gap-3 hidden">
        <i data-feather="map-pin"></i><span>Rastrear</span>
      </a>
      <a href="/rating" id="sidebarRating" class="sidebar-item gap-3 hidden">
        <i data-feather="star"></i><span>Avaliação</span>
      </a>
      <a href="/recarga" id="sidebarCard" class="sidebar-item gap-3 hidden">
        <i data-feather="credit-card"></i><span>Meu Cartão</span>
      </a>
      <a href="/profile" id="sidebarProfile" class="sidebar-item gap-3 hidden">
        <i data-feather="user"></i><span>Meu Perfil</span>
      </a>
      <a href="#" id="sidebarHistory" class="sidebar-item gap-3 hidden">
        <i data-feather="clock"></i><span>Histórico</span>
      </a>
      <div style="margin-top:auto">
        <button onclick="logout()" class="sidebar-item gap-3">
          <i data-feather="log-out"></i><span>Sair</span>
        </button>
      </div>
    `;

    this.injectLogo(sidebar);
    this.setActivePage(sidebar);

    toggle.addEventListener('click', () => this.open(sidebar, overlay));
    overlay.addEventListener('click', () => this.close(sidebar, overlay));
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') this.close(sidebar, overlay);
    });
  },

  injectLogo(sidebar) {
    const logo = document.createElement('div');
    logo.className = 'sidebar-logo';
    logo.innerHTML = `
      <span class="sidebar-logo-icon">
        <img src="/static/img/icone.png" alt="BusZapp" />
      </span>
      <span class="sidebar-logo-text">BusZapp</span>
    `;
    sidebar.prepend(logo);
  },

  setActivePage(sidebar) {
    const norm = p => (p || '').replace(/^\//, '').replace(/\.html$/, '') || 'index';
    const current = norm(window.location.pathname.split('/').pop());
    sidebar.querySelectorAll('a.sidebar-item').forEach(a => {
      const href = norm(a.getAttribute('href'));
      if (href === current) a.classList.add('sidebar-item-active');
    });
  },

  applyRole(user) {
    if (!user) return;
    const isAdmin = user.role === 'admin';
    const adminIds = ['sidebarAdmin', 'sidebarDrivers', 'sidebarFleet', 'sidebarRoutes'];
    const userIds  = ['sidebarHome', 'sidebarTrack', 'sidebarRating', 'sidebarCard', 'sidebarProfile'];
    adminIds.forEach(id => document.getElementById(id)?.classList.toggle('hidden', !isAdmin));
    userIds.forEach(id  => document.getElementById(id)?.classList.toggle('hidden', isAdmin));
  },

  open(sidebar, overlay) {
    sidebar.classList.add('open');
    overlay?.classList.add('visible');
  },
  close(sidebar, overlay) {
    sidebar?.classList.remove('open');
    overlay?.classList.remove('visible');
  },
};

// ── Utilities ─────────────────────────────────────────────────────────────────

function escapeHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

function formatCurrency(value) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
}

function formatDate(isoString) {
  if (!isoString) return '—';
  return new Date(isoString).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

function greeting(name = '') {
  const h = new Date().getHours();
  const period = h >= 5 && h < 12 ? 'Bom dia'
              : h >= 12 && h < 18 ? 'Boa tarde'
              : 'Boa noite';
  return name ? `${period}, ${name}` : period;
}

// ── Boot ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  DarkMode.init();
  Sidebar.init();
  if (typeof feather !== 'undefined') feather.replace();
  try {
    const user = await API.get('/api/auth/profile');
    Sidebar.applyRole(user);
  } catch {}
});
