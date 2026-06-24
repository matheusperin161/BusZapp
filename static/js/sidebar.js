/**
 * BuszApp · Sidebar
 *
 * Injeta a sidebar do design system (.bz-sidebar) e renderiza itens conforme
 * o papel do usuário. Substitui qualquer marcação manual de <nav class="sidebar">
 * nas páginas.
 *
 * Uso:
 *   <script src="./js/sidebar.js"></script>
 *
 * Opcionalmente, defina o papel inicial via data-role no script tag para evitar
 * uma "chacoalhada" enquanto o perfil é carregado da API:
 *   <script src="./js/sidebar.js" data-role="admin"></script>
 *
 * API global:
 *   Sidebar.init()                 — chama uma vez (já chama no DOMContentLoaded)
 *   Sidebar.applyRole(user|role)   — atualiza items quando o perfil chegar
 *   Sidebar.open() / Sidebar.close()
 */
(function () {
  const NO_SIDEBAR_PAGES = new Set([
    '', 'index', 'login', 'register', 'forgot-password', 'terms'
  ]);

  // ── Config de itens por papel ──────────────────────────────────────────────
  // Ordem do array = ordem de renderização. Cada item tem href, icon (Feather)
  // e label. Item com action: 'logout' vira botão de sair no footer.
  const ITEMS_BY_ROLE = {
    passageiro: [
      { href: '/dashboard',       icon: 'home',        label: 'Início' },
      { href: '/acompanhamento',  icon: 'map-pin',     label: 'Acompanhar' },
      { href: '/recarga',         icon: 'credit-card', label: 'Recarga' },
      { href: '/rating',          icon: 'star',        label: 'Avaliação' },
      { href: '/profile',         icon: 'user',        label: 'Meu Perfil' },
    ],
    motorista: [
      { href: '/motorista',       icon: 'truck',       label: 'Painel' },
      { href: '/profile',         icon: 'user',        label: 'Meu Perfil' },
    ],
    admin: [
      { href: '/admin',           icon: 'layout',      label: 'Visão geral' },
      { href: '/add-driver',      icon: 'users',       label: 'Motoristas' },
      { href: '/add-vehicle',     icon: 'truck',       label: 'Frota' },
      { href: '/admin-rotas',     icon: 'map',         label: 'Rotas' },
      { href: '/profile',         icon: 'user',        label: 'Meu Perfil' },
    ],
  };

  // Item de saída comum a todas as funções (vai no rodapé).
  const LOGOUT_ITEM = { icon: 'log-out', label: 'Sair', action: 'logout' };

  function pageSlug() {
    const last = (window.location.pathname.split('/').pop() || '').toLowerCase();
    return last.replace(/\.html$/, '');
  }

  function normalize(href) {
    if (!href) return '';
    return href.replace(/^\//, '').replace(/\.html$/, '').toLowerCase();
  }

  function buildItem(item) {
    const isAction = item.action === 'logout';
    const tag = isAction ? 'button' : 'a';
    const el = document.createElement(tag);
    el.className = 'bz-sidebar-item sidebar-item';
    if (isAction) {
      el.type = 'button';
      el.addEventListener('click', () => {
        if (typeof window.logout === 'function') window.logout();
      });
    } else {
      el.href = item.href;
    }
    el.innerHTML = `<i data-feather="${item.icon}"></i><span>${item.label}</span>`;
    return el;
  }

  function buildLogo() {
    const logo = document.createElement('div');
    logo.className = 'bz-sidebar-logo sidebar-logo';
    logo.innerHTML = `
      <span class="bz-sidebar-logo-icon sidebar-logo-icon">
        <img src="/static/img/icone.png" alt="BusZapp" />
      </span>
      <span class="bz-sidebar-logo-text sidebar-logo-text">BusZapp</span>
    `;
    return logo;
  }

  // ── Estado ─────────────────────────────────────────────────────────────────
  let sidebarEl = null;
  let overlayEl = null;
  let toggleEl  = null;
  let currentRole = null;
  let mounted = false;

  function ensureMount() {
    if (mounted) return;

    sidebarEl = document.getElementById('sidebar');
    if (!sidebarEl) {
      sidebarEl = document.createElement('nav');
      sidebarEl.id = 'sidebar';
      sidebarEl.setAttribute('aria-label', 'Navegação principal');
      document.body.insertAdjacentElement('afterbegin', sidebarEl);
    }
    sidebarEl.className = 'bz-sidebar sidebar flex flex-col pb-4';

    overlayEl = document.getElementById('sidebarOverlay');
    if (!overlayEl) {
      overlayEl = document.createElement('div');
      overlayEl.id = 'sidebarOverlay';
      document.body.insertAdjacentElement('afterbegin', overlayEl);
    }
    overlayEl.className = 'bz-sidebar-overlay sidebar-overlay';

    toggleEl = document.getElementById('menuToggle');
    if (!toggleEl) {
      toggleEl = document.createElement('button');
      toggleEl.id = 'menuToggle';
      toggleEl.setAttribute('aria-label', 'Menu');
      toggleEl.innerHTML = '<i data-feather="menu" class="w-6 h-6"></i>';
      document.body.insertAdjacentElement('afterbegin', toggleEl);
    }
    toggleEl.className = 'bz-menu-toggle menu-toggle';

    toggleEl.addEventListener('click', () => Sidebar.open());
    overlayEl.addEventListener('click', () => Sidebar.close());
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') Sidebar.close();
    });

    mounted = true;
  }

  function render(role) {
    if (!sidebarEl) return;
    const items = ITEMS_BY_ROLE[role] || ITEMS_BY_ROLE.passageiro;
    sidebarEl.innerHTML = '';
    sidebarEl.appendChild(buildLogo());
    items.forEach(item => sidebarEl.appendChild(buildItem(item)));

    const footer = document.createElement('div');
    footer.style.marginTop = 'auto';
    footer.appendChild(buildItem(LOGOUT_ITEM));
    sidebarEl.appendChild(footer);

    highlightActive();
    if (typeof window.feather !== 'undefined') window.feather.replace();
  }

  function highlightActive() {
    if (!sidebarEl) return;
    const current = pageSlug();
    sidebarEl.querySelectorAll('a.bz-sidebar-item').forEach(a => {
      const isActive = normalize(a.getAttribute('href')) === current;
      a.classList.toggle('active', isActive);
      a.classList.toggle('sidebar-item-active', isActive);
    });
  }

  function readInitialRole() {
    const script = document.currentScript
      || Array.from(document.scripts).reverse().find(s => /sidebar\.js/.test(s.src));
    const declared = script?.dataset?.role;
    if (declared && ITEMS_BY_ROLE[declared]) return declared;
    return null;
  }

  // ── API pública ────────────────────────────────────────────────────────────
  const Sidebar = {
    init() {
      if (NO_SIDEBAR_PAGES.has(pageSlug())) return;
      ensureMount();
      const role = currentRole || readInitialRole() || 'passageiro';
      currentRole = role;
      render(role);
    },

    /** Aceita um objeto { role } (do /api/auth/profile) ou uma string. */
    applyRole(input) {
      if (!input) return;
      const role = typeof input === 'string' ? input : input.role;
      if (!role || !ITEMS_BY_ROLE[role]) return;
      if (role === currentRole) return;
      currentRole = role;
      if (mounted) render(role);
    },

    open() {
      sidebarEl?.classList.add('open');
      overlayEl?.classList.add('visible');
    },

    close() {
      sidebarEl?.classList.remove('open');
      overlayEl?.classList.remove('visible');
    },
  };

  window.Sidebar = Sidebar;

  // Auto-init quando o DOM estiver pronto. Idempotente — chamadas extras viram no-op
  // depois da primeira renderização (a menos que applyRole mude o papel).
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => Sidebar.init());
  } else {
    Sidebar.init();
  }
})();
