/**
 * BuszApp · Bottom Nav (mobile)
 *
 * Injeta a barra inferior de navegação (.bz-bottom-nav). Visível apenas em
 * viewports < 768px — escondida via CSS no desktop.
 *
 * Uso:
 *   <script src="./js/bottom-nav.js"></script>
 *
 * Opcionalmente, defina o papel inicial:
 *   <script src="./js/bottom-nav.js" data-role="admin"></script>
 *
 * API global:
 *   BottomNav.applyRole(user|role)   — atualiza items quando o perfil chegar
 */
(function () {
  const NO_NAV_PAGES = new Set([
    '', 'index', 'login', 'register', 'forgot-password', 'terms'
  ]);

  const ITEMS_BY_ROLE = {
    passageiro: [
      { href: '/dashboard',      icon: 'home',        label: 'Início' },
      { href: '/acompanhamento', icon: 'map-pin',     label: 'Mapa' },
      { href: '/recarga',        icon: 'credit-card', label: 'Recarga' },
      { href: '/rating',         icon: 'star',        label: 'Avaliar' },
      { href: '/profile',        icon: 'user',        label: 'Perfil' },
    ],
    motorista: [
      { href: '/motorista',      icon: 'truck',       label: 'Painel' },
      { href: '/profile',        icon: 'user',        label: 'Perfil' },
    ],
    admin: [
      { href: '/admin',          icon: 'layout',      label: 'Geral' },
      { href: '/add-driver',     icon: 'users',       label: 'Pessoas' },
      { href: '/admin-rotas',    icon: 'map',         label: 'Rotas' },
      { href: '/profile',        icon: 'user',        label: 'Perfil' },
    ],
  };

  function pageSlug() {
    return (window.location.pathname.split('/').pop() || '').toLowerCase().replace(/\.html$/, '');
  }

  function normalize(href) {
    if (!href) return '';
    return href.replace(/^\//, '').replace(/\.html$/, '').toLowerCase();
  }

  function buildItem(item) {
    const a = document.createElement('a');
    a.className = 'bz-bottom-nav-item';
    a.href = item.href;
    a.innerHTML = `<i data-feather="${item.icon}"></i><span>${item.label}</span>`;
    return a;
  }

  let navEl = null;
  let currentRole = null;
  let mounted = false;

  function ensureMount() {
    if (mounted) return;
    navEl = document.getElementById('bottomNav');
    if (!navEl) {
      navEl = document.createElement('nav');
      navEl.id = 'bottomNav';
      navEl.setAttribute('aria-label', 'Navegação inferior');
      document.body.appendChild(navEl);
    }
    navEl.className = 'bz-bottom-nav';
    mounted = true;
  }

  function render(role) {
    if (!navEl) return;
    const items = ITEMS_BY_ROLE[role] || ITEMS_BY_ROLE.passageiro;
    navEl.style.gridTemplateColumns = `repeat(${items.length}, 1fr)`;
    navEl.innerHTML = '';
    items.forEach(item => navEl.appendChild(buildItem(item)));
    highlightActive();
    if (typeof window.feather !== 'undefined') window.feather.replace();
  }

  function highlightActive() {
    if (!navEl) return;
    const current = pageSlug();
    navEl.querySelectorAll('a.bz-bottom-nav-item').forEach(a => {
      a.classList.toggle('active', normalize(a.getAttribute('href')) === current);
    });
  }

  function readInitialRole() {
    const script = document.currentScript
      || Array.from(document.scripts).reverse().find(s => /bottom-nav\.js/.test(s.src));
    const declared = script?.dataset?.role;
    if (declared && ITEMS_BY_ROLE[declared]) return declared;
    return null;
  }

  const BottomNav = {
    init() {
      if (NO_NAV_PAGES.has(pageSlug())) return;
      ensureMount();
      const role = currentRole || readInitialRole() || 'passageiro';
      currentRole = role;
      render(role);
    },

    applyRole(input) {
      if (!input) return;
      const role = typeof input === 'string' ? input : input.role;
      if (!role || !ITEMS_BY_ROLE[role]) return;
      if (role === currentRole) return;
      currentRole = role;
      if (mounted) render(role);
    },
  };

  window.BottomNav = BottomNav;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => BottomNav.init());
  } else {
    BottomNav.init();
  }
})();
