// Minimal service worker: makes the app installable. It deliberately caches nothing;
// offline writing is a later phase and must never serve stale project data.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});
