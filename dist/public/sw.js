const CACHE = "original-shell-v26";
const APP_MANIFEST = "/api/app-manifest.webmanifest";
const PRECACHE = ["/", "/offline.html", "/manifest.webmanifest", "/app-icon-180-v2.png", "/app-icon-192-v3.png", "/app-icon-512-v3.png", "/app-icon-512-v2.png", "/notif-icon-v3.png", "/notif-badge-v3.png", APP_MANIFEST];
self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(PRECACHE)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith("original-shell-") && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname === APP_MANIFEST) {
    event.respondWith(caches.open(CACHE).then(async cache => {
      try {
        const response = await fetch(request);
        if (response.ok) await cache.put(request, response.clone());
        return response;
      } catch {
        return (await cache.match(request)) || new Response("{}", { status: 503, headers: { "Content-Type": "application/manifest+json" } });
      }
    }));
    return;
  }
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/manus-storage/") || url.pathname.startsWith("/__manus/") || url.pathname.startsWith("/manus-oauth/")) return;
  if (request.mode === "navigate") {
    event.respondWith(fetch(request).then(response => {
      if (response.ok) {
        const copy = response.clone();
        caches.open(CACHE).then(cache => cache.put("/", copy));
      }
      return response;
    }).catch(async () => (await caches.match("/")) || (await caches.match("/offline.html"))));
    return;
  }
  if (url.pathname.includes("/assets/")) {
    event.respondWith(caches.match(request).then(cached => cached || fetch(request).then(response => {
      if (response.ok) caches.open(CACHE).then(cache => cache.put(request, response.clone()));
      return response;
    })));
  }
});

self.addEventListener("push", event => {
  if (!event.data) return;
  event.waitUntil((async () => {
    try {
      const payload = event.data.json();
      const title = typeof payload.title === "string" ? payload.title.slice(0, 100) : "🌿 متجر أورجنال";
      const body = typeof payload.body === "string" ? payload.body.slice(0, 300) : "تم تحديث حالة طلبك";
      const requestedUrl = typeof payload.url === "string" ? payload.url : "/orders";
      const url = requestedUrl.startsWith("/") && !requestedUrl.startsWith("//") ? requestedUrl : "/orders";
      const tag = typeof payload.tag === "string" ? payload.tag.slice(0, 100) : "original-order-update";
      const isAdminUrl = url.startsWith("/admin");
      await self.registration.showNotification(title, {
        body,
        icon: "/notif-icon-v3.png",
        badge: "/notif-badge-v3.png",
        tag,
        renotify: true,
        requireInteraction: isAdminUrl,
        vibrate: isAdminUrl ? [220, 100, 220, 100, 260] : [180, 80, 180],
        actions: [{ action: "open_order", title: isAdminUrl ? "📋 فتح الطلب في الإدارة" : "📦 تتبع حالة الطلب" }],
        data: { url },
        dir: "rtl",
        lang: "ar",
      });
    } catch (error) {
      console.warn("[PWA] Ignored an invalid push message", error instanceof Error ? error.message : "unknown error");
    }
  })());
});

self.addEventListener("notificationclick", event => {
  event.notification.close();
  const requestedUrl = typeof event.notification.data?.url === "string" ? event.notification.data.url : "/orders";
  const url = requestedUrl.startsWith("/") && !requestedUrl.startsWith("//") ? new URL(requestedUrl, self.location.origin) : new URL("/orders", self.location.origin);
  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const client of windows) {
      if (!client.url.startsWith(self.location.origin)) continue;
      await client.navigate(url.href);
      await client.focus();
      return;
    }
    await self.clients.openWindow(url.href);
  })());
});
