const CACHE_NAME = 'rto-autopilot-v1';
const OFFLINE_URL = '/offline';

// Assets to cache immediately on install (app shell)
const CACHE_ASSETS = [
  '/',
  '/static/icon-192.png',
  '/static/icon-512.png',
  'https://cdn.tailwindcss.com'
];

// Install event - cache essential assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[Service Worker] Caching app shell');
        return cache.addAll(CACHE_ASSETS);
      })
      .catch((error) => {
        console.error('[Service Worker] Install failed:', error);
      })
  );
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== CACHE_NAME) {
              console.log('[Service Worker] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
  );
  self.clients.claim();
});

// Fetch event - serve from cache, fall back to network
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip API routes (don't cache sensitive data)
  if (event.request.url.includes('/api/') ||
      event.request.url.includes('/login') ||
      event.request.url.includes('/logout') ||
      event.request.url.includes('/signup')) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then((cachedResponse) => {
        // Return cached version if available
        if (cachedResponse) {
          // Update cache in background
          fetchAndCache(event.request);
          return cachedResponse;
        }

        // Otherwise fetch from network
        return fetchAndCache(event.request);
      })
      .catch(() => {
        // If both cache and network fail, show offline page
        if (event.request.destination === 'document') {
          return caches.match(OFFLINE_URL);
        }
      })
  );
});

// Helper to fetch and cache a request
function fetchAndCache(request) {
  return fetch(request)
    .then((response) => {
      // Don't cache non-successful responses
      if (!response || response.status !== 200 || response.type !== 'basic') {
        return response;
      }

      // Clone the response since it can only be consumed once
      const responseToCache = response.clone();

      caches.open(CACHE_NAME)
        .then((cache) => {
          cache.put(request, responseToCache);
        });

      return response;
    })
    .catch((error) => {
      console.error('[Service Worker] Fetch failed:', error);
      throw error;
    });
}
