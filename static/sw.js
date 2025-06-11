const CACHE_NAME = 'easyall-mp3-v1';
const urlsToCache = [
  '/mp3',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

// Installer service worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Cache åpnet');
        return cache.addAll(urlsToCache);
      })
  );
});

// Lytt etter fetch-hendelser
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Returner cached versjon hvis tilgjengelig
        if (response) {
          return response;
        }
        return fetch(event.request);
      }
    )
  );
});

// Oppdater service worker
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('Sletter gammel cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});