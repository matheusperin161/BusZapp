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

  const ICONS = {
    success: '✓', error: '✕', warning: '⚠', info: 'ℹ',
  };

  function show(message, type = 'info', duration = 4000) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <span style="font-size:1.1rem;flex-shrink:0">${ICONS[type] || ICONS.info}</span>
      <span style="flex:1;font-size:.875rem">${escapeHtml(message)}</span>
      <button class="toast-dismiss" onclick="this.closest('.toast').remove()" aria-label="Fechar"
        style="background:none;border:none;cursor:pointer;font-size:1rem;color:inherit;opacity:.6;">✕</button>
    `;
    getContainer().appendChild(toast);
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
    if (redirectIfGuest) window.location.href = '/login.html';
    return null;
  }
}

async function requireAdmin() {
  const user = await checkAuth(true);
  if (user && user.role !== 'admin') {
    Toast.error('Acesso restrito a administradores.');
    setTimeout(() => window.location.href = '/dashboard.html', 1500);
    return null;
  }
  return user;
}

async function logout() {
  await API.post('/api/auth/logout').catch(() => {});
  window.location.href = '/login.html';
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
    const sidebar  = document.getElementById('sidebar');
    const toggle   = document.getElementById('menuToggle');
    const overlay  = document.getElementById('sidebarOverlay');
    if (!sidebar || !toggle) return;

    toggle.addEventListener('click', () => this.open(sidebar, overlay));
    overlay?.addEventListener('click', () => this.close(sidebar, overlay));
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') this.close(sidebar, overlay);
    });
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

// ── Boot ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  DarkMode.init();
  Sidebar.init();
  if (typeof feather !== 'undefined') feather.replace();
});
