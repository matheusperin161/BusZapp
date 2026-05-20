const CACHE_VERSION = 'buszapp-v1';

// Static assets that are safe to cache indefinitely
const STATIC_ASSETS = [
  '/static/css/main.css',
  '/static/js/app.js',
  '/static/js/notifications.js',
  '/static/img/icone.png',
  '/static/img/icon-192x192.png',
  '/static/img/icon-512x512.png',
  '/static/manifest.json',
];

// Pages cached on first visit (network-first, fallback to cache)
const PAGE_ASSETS = [
  '/dashboard.html',
  '/acompanhamento.html',
  '/recarga.html',
  '/profile.html',
  '/rating.html',
  '/login.html',
  '/register.html',
  '/forgot-password.html',
];

// API prefixes — always network-only (real-time data)
const NETWORK_ONLY_PREFIXES = [
  '/api/',
  '/socket.io/',
  '/tracking',
];

// ── Install: pre-cache static assets ─────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) =>
      cache.addAll(STATIC_ASSETS)
    ).then(() => self.skipWaiting())
  );
});

// ── Activate: remove old caches ───────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// ── Fetch: routing strategy ───────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle same-origin requests
  if (url.origin !== self.location.origin) return;

  // Network-only: APIs, Socket.IO, real-time endpoints
  if (NETWORK_ONLY_PREFIXES.some((p) => url.pathname.startsWith(p))) {
    return; // let the browser handle it normally
  }

  // Static assets: cache-first
  if (STATIC_ASSETS.some((a) => url.pathname === a)) {
    event.respondWith(
      caches.match(request).then((cached) =>
        cached || fetch(request).then((res) => {
          const clone = res.clone();
          caches.open(CACHE_VERSION).then((c) => c.put(request, clone));
          return res;
        })
      )
    );
    return;
  }

  // HTML pages: network-first, fallback to cache
  if (request.mode === 'navigate' || url.pathname.endsWith('.html')) {
    event.respondWith(
      fetch(request)
        .then((res) => {
          const clone = res.clone();
          caches.open(CACHE_VERSION).then((c) => c.put(request, clone));
          return res;
        })
        .catch(() =>
          caches.match(request).then((cached) =>
            cached || caches.match('/login.html')
          )
        )
    );
    return;
  }

  // Everything else: network-first
  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});
