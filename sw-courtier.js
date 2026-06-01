/* =========================================================================
   Service Worker - Capital Norvex Espace Courtier
   Stratégie minimale : network-first pour les pages, cache-first pour assets.
   Pas de cache agressif sur les endpoints API pour garder données fraîches.
   ========================================================================= */
const CACHE_NAME = 'cn-courtier-v1';
const CORE_ASSETS = [
  '/espace-courtier.html',
  '/manifest-courtier.json',
  '/icon-192.png',
  '/icon-512.png',
  '/assets/logo-norvex-officiel.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Bypass : ne touche jamais aux endpoints API
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/.netlify/')) {
    return; // laisse le navigateur gérer normalement
  }

  // Navigation requests : network-first, fallback cache
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => caches.match('/espace-courtier.html'))
    );
    return;
  }

  // Assets (images, fonts, css, js) : cache-first
  event.respondWith(
    caches.match(event.request).then((cached) => {
      return (
        cached ||
        fetch(event.request)
          .then((res) => {
            if (res && res.status === 200 && res.type === 'basic') {
              const copy = res.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy)).catch(() => {});
            }
            return res;
          })
          .catch(() => cached)
      );
    })
  );
});
