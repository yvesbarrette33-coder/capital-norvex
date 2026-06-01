// 🚨 SERVICE WORKER AUTO-DÉSINSCRIPTION 2026-05-25
// Ce SW se désinscrit lui-même et purge tous les caches pour éviter
// les bugs de polling get-result / analyze-background causés par
// l'interception sur des endpoints Netlify Functions critiques.
// Score Norvex = porte d'entrée client = ZERO risk policy.

self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    // 1. Purger tous les caches
    const keys = await caches.keys();
    await Promise.all(keys.map(k => caches.delete(k)));
    // 2. Désinscrire le SW
    await self.registration.unregister();
    // 3. Forcer reload de tous les clients pour qu'ils repartent sans SW
    const clients = await self.clients.matchAll({ type: 'window' });
    clients.forEach(client => client.navigate(client.url));
  })());
});

// Aucun listener fetch — toutes les requêtes passent directement au réseau.
