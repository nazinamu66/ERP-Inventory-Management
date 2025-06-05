const CACHE_NAME = "inventrax-cache-v1";
const urlsToCache = [
  "/",
  "/login/",
  // "/static/css/main.css", // example
  // "/static/js/main.js",   // example
  "/static/icons/icon-192x192.png",
  "/static/icons/icon-512x512.png"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(urlsToCache);
    })
  );
});

self.addEventListener("fetch", event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});
