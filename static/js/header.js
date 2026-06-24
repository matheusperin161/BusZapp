/**
 * BuszApp · Header
 *
 * Header padronizado do design system. Usa .bz-header (branco no desktop,
 * gradiente no mobile via CSS). Posicionado de forma sticky no topo.
 *
 * Uso:
 *   <script src="./js/header.js"
 *           data-title="Painel"
 *           data-subtitle="Olá, Guilherme"
 *           data-show-theme="true"
 *           data-show-notifications="true"
 *           data-show-profile="true"
 *           data-title-id="headerTitle"
 *           data-subtitle-id="headerSub"></script>
 *
 * Atributos data-*:
 *   data-title              — texto do título (default: "BusZapp")
 *   data-subtitle           — subtítulo opcional (só aparece se data-subtitle-id também for definido)
 *   data-show-theme         — "false" para esconder botão de tema (default: visível)
 *   data-show-notifications — "true" para mostrar sino de notificações
 *   data-show-profile       — "true" para mostrar botão de perfil
 *   data-title-id           — id do elemento h1 (para atualizar dinamicamente)
 *   data-subtitle-id        — id do elemento subtítulo (idem)
 */
(function () {
  const s = document.currentScript;

  const title       = s.dataset.title       || 'BuszApp';
  const subtitle    = s.dataset.subtitle    || '';
  const showTheme   = s.dataset.showTheme   !== 'false';
  const showNotif   = s.dataset.showNotifications === 'true';
  const showProfile = s.dataset.showProfile === 'true';
  const titleId     = s.dataset.titleId     || '';
  const subtitleId  = s.dataset.subtitleId  || '';

  const themeBtn = showTheme ? `
    <button id="themeToggle" type="button"
            class="bz-header-icon-btn"
            onclick="DarkMode.toggle();updateThemeIcon&&updateThemeIcon()"
            title="Alternar tema" aria-label="Alternar tema">
      <i data-feather="moon" class="w-5 h-5"></i>
    </button>` : '';

  const notifBlock = showNotif ? `
    <div class="relative">
      <button id="notificationButton" type="button" class="bz-header-icon-btn notif-bell-btn" aria-label="Notificações">
        <i data-feather="bell" class="w-5 h-5"></i>
        <span id="notificationBadge" class="hidden notif-badge"></span>
      </button>
      <div id="notificationDropdown" class="hidden notif-dropdown">
        <div class="notif-dropdown-header">
          <div class="notif-dropdown-title">
            <div class="notif-dropdown-icon-wrap">
              <i data-feather="bell" class="w-4 h-4"></i>
            </div>
            <span>Notificações</span>
          </div>
          <button id="markAllAsRead" type="button" class="notif-mark-read-btn">Marcar lidas</button>
        </div>
        <div id="notificationList" class="notif-list">
          <div id="noNotificationsMessage" class="notif-empty">
            <div class="notif-empty-icon">🔔</div>
            <p class="notif-empty-title">Nenhuma notificação</p>
            <p class="notif-empty-sub">Você está em dia!</p>
          </div>
        </div>
      </div>
    </div>` : '';

  const profileBtn = showProfile ? `
    <button type="button" class="bz-header-icon-btn"
            onclick="window.location.href='/profile'" aria-label="Perfil">
      <i data-feather="user" class="w-5 h-5"></i>
    </button>` : '';

  const titleAttrs    = titleId    ? ` id="${titleId}"`    : '';
  const subtitleAttrs = subtitleId ? ` id="${subtitleId}"` : '';
  const subtitleEl    = subtitleId
    ? `<p class="bz-header-subtitle"${subtitleAttrs}>${subtitle}</p>`
    : '';

  const html = `
    <header class="bz-header">
      <div class="bz-header-titles">
        <h1 class="bz-header-title"${titleAttrs}>${title}</h1>
        ${subtitleEl}
      </div>
      <div class="bz-header-actions">
        ${themeBtn}
        ${notifBlock}
        ${profileBtn}
      </div>
    </header>`;

  s.insertAdjacentHTML('afterend', html);
})();
