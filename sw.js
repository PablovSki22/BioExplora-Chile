const CACHE_NAME = 'bioexplora-cache-v1';
const urlsToCache = [
  '/',
  'https://raw.githubusercontent.com/PablovSki22/BioExplora-Chile/main/favicon.ico'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
