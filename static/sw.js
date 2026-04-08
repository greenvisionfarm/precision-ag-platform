const CACHE_NAME = "field-mapper-v2-20260407";
const ASSETS_TO_CACHE = [
  "/",
  "/static/css/style.css",
  // JS модули НЕ кэшируем — они всегда загружаются из сети с ?v= cache bust
  "https://code.jquery.com/jquery-3.7.1.min.js",
  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
  "https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.js",
  "https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css",
  "https://cdn.datatables.net/1.11.5/js/jquery.dataTables.js",
  "https://cdn.datatables.net/1.11.5/css/jquery.dataTables.css",
];

// Установка: кэшируем статику
self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS_TO_CACHE))
      .then(() => self.skipWaiting())
  );
});

// Активация: чистим старые кэши
self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
      );
    })
  );
});

// Перехват запросов
self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);

  // Запросы с query string (cache busting) — всегда из сети
  if (url.search) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Для API и страниц всегда идем в сеть
  if (url.pathname.startsWith("/api/") || !ASSETS_TO_CACHE.includes(url.pathname)) {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(event.request))
    );
  } else {
    // Для статики берем из кэша
    event.respondWith(
      caches.match(event.request).then(response => {
        return response || fetch(event.request);
      })
    );
  }
});
