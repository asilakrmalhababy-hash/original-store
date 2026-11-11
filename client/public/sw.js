const CACHE = "original-shell-v126";
const PRECACHE = ["/", "/offline.html", "/manifest.webmanifest", "/app-icon-180-v85.png", "/app-icon-192-v85.png", "/app-icon-512-v85.png", "/notif-icon-v3.png", "/notif-badge-v3.png"];

self.addEventListener("install", event => {
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(PRECACHE).catch(() => {})));
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/") && !url.pathname.startsWith("/api/fast-img/")) return;

  if (request.mode === "navigate") {
    event.respondWith(caches.open(CACHE).then(async cache => {
      try {
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), 2500);
        const res = await fetch(request, { signal: ctrl.signal });
        clearTimeout(timer);
        if (res && res.ok) {
          cache.put("/", res.clone());
          return res;
        }
      } catch {}
      return (await cache.match("/")) || (await cache.match("/offline.html")) || fetch(request);
    }));
    return;
  }

  if (url.pathname.startsWith("/api/fast-img/") || url.pathname.includes("/assets/") || url.pathname.endsWith(".png") || url.pathname.endsWith(".webmanifest")) {
    event.respondWith(caches.open(CACHE).then(async cache => {
      const cached = await cache.match(request, { ignoreSearch: !url.pathname.startsWith("/api/fast-img/") });
      if (cached) {
        const cct = (cached.headers && cached.headers.get("content-type")) || "";
        if (!(url.pathname.endsWith(".js") && cct.includes("text/html"))) return cached;
      }
      try {
        const res = await fetch(request);
        const ct = (res && res.headers && res.headers.get("content-type")) || "";
        if (res && res.ok && !(url.pathname.endsWith(".js") && ct.includes("text/html"))) {
          cache.put(request, res.clone());
        }
        return res;
      } catch {
        return new Response("", { status: 504 });
      }
    }));
    return;
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
