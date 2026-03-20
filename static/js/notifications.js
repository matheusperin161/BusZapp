/**
 * BuszApp – Notification System
 * Handles real-time and persistent notifications.
 */

const NOTIF_CONFIG = {
  MIN_BALANCE:        5.00,
  MAX_STORED:         50,
  EXPIRY_MS:          7 * 24 * 60 * 60 * 1000, // 7 days
  STORAGE_KEY:        'buszapp_notifications', // base — sufixo _userId adicionado dinamicamente
  DELAY_INTERVAL_MS:  60_000,
  ENABLE_DESKTOP:     true,
};

const TYPE_ICONS = {
  line_delay:  '🚌',
  low_balance: '💳',
  success:     '✓',
  warning:     '⚠️',
  error:       '✕',
  info:        'ℹ️',
};

// ── Notification Model ────────────────────────────────────────────────────────

class AppNotification {
  constructor(title, message, type = 'info', options = {}) {
    this.id        = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    this.title     = title;
    this.message   = message;
    this.type      = type;
    this.timestamp = Date.now();
    this.read      = false;
    this.options   = options;
    this.time      = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }

  static fromJSON(obj) {
    const n = new AppNotification(obj.title, obj.message, obj.type, obj.options);
    Object.assign(n, { id: obj.id, timestamp: obj.timestamp, read: obj.read, time: obj.time });
    return n;
  }
}

// ── Manager ───────────────────────────────────────────────────────────────────

class NotificationManager {
  constructor() {
    this._items = [];
    this._load();
  }

  // Public API
  add(title, message, type = 'info', options = {}) {
    const n = new AppNotification(title, message, type, options);
    this._items.unshift(n);
    if (this._items.length > NOTIF_CONFIG.MAX_STORED) this._items.pop();
    this._save();
    this._render(n);
    this._updateBadge();
    this._desktopNotify(n);
    return n;
  }

  remove(id) {
    this._items = this._items.filter(n => n.id !== id);
    this._save();
    this._updateBadge();
  }

  markRead(id) {
    const n = this._items.find(n => n.id === id);
    if (n) { n.read = true; this._save(); this._updateBadge(); }
  }

  markAllRead() {
    this._items.forEach(n => n.read = true);
    this._save();
    this._updateBadge();
  }

  clearAll() {
    this._items = [];
    this._save();
    this._updateBadge();
  }

  getAll()              { return this._items; }
  getUnread()           { return this._items.filter(n => !n.read); }
  getByType(type)       { return this._items.filter(n => n.type === type); }

  // Internal
  _storageKey() {
    // Chave separada por usuário para evitar vazamento entre contas
    const uid = localStorage.getItem('buszapp_user_id') || 'guest';
    return `${NOTIF_CONFIG.STORAGE_KEY}_${uid}`;
  }

  _load() {
    try {
      const raw = localStorage.getItem(this._storageKey());
      if (raw) {
        const parsed = JSON.parse(raw);
        const cutoff = Date.now() - NOTIF_CONFIG.EXPIRY_MS;
        this._items = parsed
          .filter(n => n.timestamp > cutoff)
          .map(n => AppNotification.fromJSON(n));
      }
    } catch { /* ignore */ }
  }

  _save() {
    try {
      localStorage.setItem(this._storageKey(), JSON.stringify(this._items));
    } catch { /* ignore */ }
  }

  _render(n) {
    const list = document.getElementById('notificationList');
    if (!list) return;
    document.getElementById('noNotificationsMessage')?.remove();

    const el = document.createElement('div');
    el.dataset.notifId = n.id;
    el.className = `notification-item ${n.type}${n.read ? '' : ' unread'}`;
    el.innerHTML = `
      <div class="notif-header">
        <div class="notif-icon-title">
          <span class="notif-icon">${TYPE_ICONS[n.type] ?? TYPE_ICONS.info}</span>
          <p class="notification-title">${escapeHtml(n.title)}</p>
        </div>
        <button data-close="${n.id}" class="notif-close-btn" aria-label="Fechar">✕</button>
      </div>
      <p class="notification-message">${escapeHtml(n.message)}</p>
      <p class="notification-time">${n.time}</p>
    `;

    el.querySelector('[data-close]').addEventListener('click', e => {
      e.stopPropagation();
      this.remove(n.id);
      el.remove();
    });

    el.addEventListener('click', () => {
      this.markRead(n.id);
      el.classList.remove('unread');
    });

    list.prepend(el);
  }

  _renderAll() {
    this._items.forEach(n => this._render(n));
  }

  _updateBadge() {
    const badge  = document.getElementById('notificationBadge');
    const btn    = document.getElementById('notificationButton');
    const unread = this.getUnread().length;
    if (badge)  badge.classList.toggle('hidden', unread === 0);
    if (btn)    btn.classList.toggle('has-unread', unread > 0);
  }

  _desktopNotify(n) {
    if (!NOTIF_CONFIG.ENABLE_DESKTOP) return;
    if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
      try {
        new Notification(n.title, { body: n.message, icon: './img/icone_site.png', tag: n.id });
      } catch { /* unsupported */ }
    }
  }
}

// ── Global Instance ───────────────────────────────────────────────────────────

const notificationManager = new NotificationManager();

// ── API Sync ──────────────────────────────────────────────────────────────────

async function syncNotificationsFromAPI() {
  try {
    const res = await fetch('/api/notifications', { credentials: 'include' });
    if (!res.ok) return;
    const list = await res.json();
    list.forEach(item => {
      const alreadyAdded = notificationManager._items.some(n => n.options?.backendId === item.id);
      if (alreadyAdded) return;
      const type = item.title.includes('Recarga')   ? 'success'
                 : item.title.includes('Atraso')    ? 'line_delay'
                 : item.title.includes('Pane')      ? 'warning'
                 : item.title.includes('Acidente')  ? 'error'
                 : item.title.includes('Saldo')     ? 'low_balance'
                 : 'info';
      notificationManager.add(item.title, item.message, type, { backendId: item.id });
    });
  } catch { /* API unavailable */ }
}

// ── Low Balance Check ─────────────────────────────────────────────────────────

function checkLowBalance(balance) {
  if (balance >= NOTIF_CONFIG.MIN_BALANCE) return;
  const todayStr = new Date().toDateString();
  const alreadyToday = notificationManager.getByType('low_balance')
    .some(n => new Date(n.timestamp).toDateString() === todayStr);
  if (!alreadyToday) {
    notificationManager.add(
      'Atenção: Saldo Baixo!',
      `Saldo atual: R$ ${balance.toFixed(2).replace('.', ',')}. Recarregue para evitar interrupções.`,
      'low_balance',
    );
  }
}

// ── Line Delay Check ──────────────────────────────────────────────────────────

async function checkLineDelays() {
  try {
    const res = await fetch('/api/lines', { credentials: 'include' });
    if (!res.ok) return;
    const { lines = [] } = await res.json();
    lines.forEach(line => {
      if (!line.delay) return;
      const title = `Atraso na ${line.name}`;
      const recentlySent = notificationManager.getByType('line_delay')
        .some(n => n.title === title && Date.now() - n.timestamp < 3_600_000);
      if (!recentlySent) {
        notificationManager.add(title, `Motivo: ${line.reason}. Atraso estimado: ${line.delay} min.`, 'line_delay');
      }
    });
  } catch { /* API not available */ }
}

// ── Dropdown Setup ────────────────────────────────────────────────────────────

function setupNotificationDropdown() {
  const btn      = document.getElementById('notificationButton');
  const dropdown = document.getElementById('notificationDropdown');
  const markAll  = document.getElementById('markAllAsRead');
  if (!btn || !dropdown) return;

  btn.addEventListener('click', e => {
    e.stopPropagation();
    const hidden = dropdown.classList.toggle('hidden');
    if (!hidden) notificationManager.markAllRead();
  });

  document.addEventListener('click', e => {
    if (!dropdown.contains(e.target) && !btn.contains(e.target)) {
      dropdown.classList.add('hidden');
    }
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') dropdown.classList.add('hidden');
  });

  markAll?.addEventListener('click', () => {
    notificationManager.markAllRead();
    dropdown.classList.add('hidden');
  });
}

// ── Init ──────────────────────────────────────────────────────────────────────

function initNotifications() {
  if (typeof Notification !== 'undefined' && Notification.permission === 'default') {
    Notification.requestPermission();
  }

  notificationManager._renderAll();
  notificationManager._updateBadge();
  setupNotificationDropdown();
  syncNotificationsFromAPI();

  setInterval(checkLineDelays, NOTIF_CONFIG.DELAY_INTERVAL_MS);

  // Polling: busca novas notificações do backend a cada 30s
  // Garante que alertas do motorista apareçam sem precisar recarregar
  setInterval(syncNotificationsFromAPI, 30_000);
}

// ── Exports ───────────────────────────────────────────────────────────────────

window.NotificationSystem = {
  manager:         notificationManager,
  add:             (...a)  => notificationManager.add(...a),
  remove:          (id)    => notificationManager.remove(id),
  markRead:        (id)    => notificationManager.markRead(id),
  markAllRead:     ()      => notificationManager.markAllRead(),
  clearAll:        ()      => notificationManager.clearAll(),
  getAll:          ()      => notificationManager.getAll(),
  getUnread:       ()      => notificationManager.getUnread(),
  checkLowBalance,
  init:            initNotifications,
};

function escapeHtml(str = '') {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initNotifications);
} else {
  initNotifications();
}
