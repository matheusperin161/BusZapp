/**
 * Componente de header compartilhado.
 * Uso: <script src="./js/header.js"
 *              data-icon="credit-card"
 *              data-title="Título"
 *              data-subtitle="Subtítulo"
 *              data-show-theme="true"
 *              data-show-notifications="true"
 *              data-show-profile="true"
 *              data-title-id="headerTitle"
 *              data-subtitle-id="headerSub">
 *       </script>
 */
(function () {
  const s = document.currentScript;

  const icon        = s.dataset.icon        || 'home';
  const title       = s.dataset.title       || 'BusZapp';
  const subtitle    = s.dataset.subtitle    || '';
  const showTheme   = s.dataset.showTheme   !== 'false';
  const showNotif   = s.dataset.showNotifications === 'true';
  const showProfile = s.dataset.showProfile === 'true';
  const titleId     = s.dataset.titleId     || '';
  const subtitleId  = s.dataset.subtitleId  || '';

  const circles = `
    <div class="absolute -top-6 -right-8 w-36 h-36 bg-white/10 rounded-full pointer-events-none"></div>
    <div class="absolute top-1 right-20 w-20 h-20 bg-white/5 rounded-full pointer-events-none"></div>
    <div class="absolute -bottom-8 left-1/3 w-28 h-28 bg-orange-300/20 rounded-full pointer-events-none"></div>
    <div class="absolute -top-4 left-2/3 w-14 h-14 bg-white/5 rounded-full pointer-events-none"></div>`;

  const themeBtn = showTheme ? `
    <button id="themeToggle" onclick="DarkMode.toggle();updateThemeIcon()"
            class="p-2.5 rounded-xl hover:bg-white/20 transition" title="Alternar tema" aria-label="Alternar tema">
      <i data-feather="moon" class="w-5 h-5"></i>
    </button>` : '';

  const notifBlock = showNotif ? `
    <div class="relative">
      <button id="notificationButton" class="notif-bell-btn relative" aria-label="Notificações">
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
          <button id="markAllAsRead" class="notif-mark-read-btn">Marcar lidas</button>
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
    <button onclick="window.location.href='profile.html'"
            class="p-2.5 rounded-xl hover:bg-white/20 transition" aria-label="Perfil">
      <i data-feather="user" class="w-5 h-5"></i>
    </button>` : '';

  const html = `<header class="bg-gradient-to-r from-yellow-400 via-yellow-500 to-orange-500 text-white shadow-xl sticky top-0 z-40 relative overflow-hidden">
    ${circles}
    <div class="w-full px-4 py-4 flex items-center relative">
      <div class="pl-14">
        <h1 class="text-2xl font-extrabold tracking-tight"${titleId ? ` id="${titleId}"` : ''}>${title}</h1>
        ${subtitleId ? `<p class="text-xs opacity-80" id="${subtitleId}">${subtitle}</p>` : ''}
      </div>
      <div class="flex items-center gap-2 relative ml-auto">
        ${themeBtn}
        ${notifBlock}
        ${profileBtn}
      </div>
    </div>
  </header>`;

  s.insertAdjacentHTML('afterend', html);
})();
