const CACHE = "original-shell-v1792828424410";
const STATE_CACHE = "original-sw-state-v1";
const STATE_KEY = "https://sw.local/state";
const APP_MANIFEST = "/api/app-manifest.webmanifest";
const PRECACHE = ["/", "/offline.html", "/manifest.webmanifest", "/app-icon-180-v2.png", "/app-icon-192-v2.png", "/app-icon-512-v2.png", APP_MANIFEST];

const STATUS_LABELS = {
  new: "تم استلام الطلب",
  preparing: "طلبك قيد التجهيز",
  ready: "طلبك جاهز للتوصيل",
  out_for_delivery: "خرج طلبك للتوصيل",
  delivered: "تم تسليم طلبك",
  cancelled: "تم إلغاء الطلب",
};

async function readSwState() {
  try {
    const cache = await caches.open(STATE_CACHE);
    const res = await cache.match(STATE_KEY);
    if (!res) return { isAdmin: false, afterId: 0, refs: [], statusMap: {}, notifiedTags: {} };
    return await res.json();
  } catch {
    return { isAdmin: false, afterId: 0, refs: [], statusMap: {}, notifiedTags: {} };
  }
}

async function writeSwState(state) {
  try {
    const cache = await caches.open(STATE_CACHE);
    await cache.put(STATE_KEY, new Response(JSON.stringify(state), { headers: { "Content-Type": "application/json" } }));
  } catch {}
}

async function pollFromServiceWorker() {
  try {
    const state = await readSwState();
    if (!state.isAdmin && (!state.refs || !state.refs.length)) return;
    const res = await fetch("/api/sw-poll", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ isAdmin: state.isAdmin, afterId: state.afterId, refs: state.refs }),
    });
    if (!res.ok) return;
    const data = await res.json();
    if (!data || !data.ok) return;
    let changed = false;
    state.notifiedTags = state.notifiedTags || {};
    state.statusMap = state.statusMap || {};

    if (state.isAdmin && typeof data.latestId === "number") {
      if (!state.afterId || state.afterId === 0) {
        if (data.latestId > 0) { state.afterId = data.latestId; changed = true; }
      } else if (Array.isArray(data.newOrders) && data.newOrders.length > 0) {
        for (const order of data.newOrders) {
          const tag = "original-new-order-" + order.id;
          if (!state.notifiedTags[tag]) {
            state.notifiedTags[tag] = Date.now();
            changed = true;
            await self.registration.showNotification("طلب جديد في أوريجنال 🔔", {
              body: "وصل الطلب " + order.orderNumber + " بإجمالي " + Number(order.total || 0).toLocaleString("en-US") + " ر.ي.",
              icon: "/app-icon-192-v2.png",
              badge: "/app-icon-192-v2.png",
              tag,
              data: { url: "/admin/orders" },
              dir: "rtl",
              lang: "ar",
              vibrate: [300, 120, 300, 120, 400],
              requireInteraction: true,
              renotify: true,
            });
          }
        }
        if (data.latestId > state.afterId) { state.afterId = data.latestId; changed = true; }
      }
    }

    if (Array.isArray(data.orders)) {
      for (const order of data.orders) {
        const sig = order.status + ":" + (order.note || "");
        const prev = state.statusMap[order.orderNumber];
        if (prev && prev !== sig) {
          const tag = "original-order-status-" + order.orderId + "-" + order.status;
          if (!state.notifiedTags[tag]) {
            state.notifiedTags[tag] = Date.now();
            const label = STATUS_LABELS[order.status] || "تغيرت حالة طلبك";
            await self.registration.showNotification("تحديث الطلب " + order.orderNumber + " 🔔", {
              body: label + (order.note ? " · " + order.note : ""),
              icon: "/app-icon-192-v2.png",
              badge: "/app-icon-192-v2.png",
              tag,
              data: { url: "/orders" },
              dir: "rtl",
              lang: "ar",
              vibrate: [250, 120, 250],
              requireInteraction: true,
              renotify: true,
            });
          }
        }
        if (prev !== sig) { state.statusMap[order.orderNumber] = sig; changed = true; }
      }
    }

    if (changed) await writeSwState(state);
  } catch {}
}

let pollTimer = null;
function startBackgroundLoop() {
  if (pollTimer) return;
  pollTimer = setInterval(() => { void pollFromServiceWorker(); }, 15000);
}
startBackgroundLoop();

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key.startsWith("original-shell-") && key !== CACHE).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
      .then(() => { startBackgroundLoop(); })
  );
});

self.addEventListener("message", event => {
  const msg = event.data;
  if (!msg || typeof msg !== "object") return;
  if (msg.type === "SYNC_SW_STATE") {
    event.waitUntil((async () => {
      const state = await readSwState();
      if (typeof msg.isAdmin === "boolean") state.isAdmin = msg.isAdmin;
      if (typeof msg.afterId === "number" && msg.afterId > (state.afterId || 0)) state.afterId = msg.afterId;
      if (Array.isArray(msg.refs)) state.refs = msg.refs;
      await writeSwState(state);
      startBackgroundLoop();
      await pollFromServiceWorker();
    })());
  }
});

self.addEventListener("periodicsync", event => {
  event.waitUntil(pollFromServiceWorker());
});

self.addEventListener("sync", event => {
  event.waitUntil(pollFromServiceWorker());
});

self.addEventListener("fetch", event => {
  startBackgroundLoop();
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
  if (url.pathname.includes("/assets/") || url.pathname.startsWith("/uploads/")) {
    event.respondWith(caches.match(request).then(cached => cached || fetch(request).then(response => {
      if (response.ok) caches.open(CACHE).then(cache => cache.put(request, response.clone()));
      return response;
    })));
  }
});

self.addEventListener("push", event => {
  event.waitUntil((async () => {
    try {
      let payload = {};
      try {
        payload = event.data ? event.data.json() : {};
      } catch {
        payload = { title: "أوريجنال 🔔", body: event.data ? event.data.text() : "يوجد إشعار جديد" };
      }
      const title = typeof payload.title === "string" && payload.title ? payload.title.slice(0, 100) : "أوريجنال 🔔";
      const body = typeof payload.body === "string" && payload.body ? payload.body.slice(0, 300) : "يوجد تحديث جديد.";
      const requestedUrl = typeof payload.url === "string" ? payload.url : "/";
      const url = requestedUrl.startsWith("/") && !requestedUrl.startsWith("//") ? requestedUrl : "/";
      const tag = typeof payload.tag === "string" && payload.tag ? payload.tag.slice(0, 100) : "original-push-" + Date.now();
      const state = await readSwState();
      state.notifiedTags = state.notifiedTags || {};
      state.notifiedTags[tag] = Date.now();
      await writeSwState(state);
      await self.registration.showNotification(title, {
        body,
        icon: "/app-icon-192-v2.png",
        badge: "/app-icon-192-v2.png",
        tag,
        data: { url },
        dir: "rtl",
        lang: "ar",
        vibrate: [300, 120, 300, 120, 400],
        requireInteraction: true,
        renotify: true,
      });
    } catch (error) {
      console.warn("[PWA] Push error", error);
    }
  })());
});

self.addEventListener("notificationclick", event => {
  event.notification.close();
  const requestedUrl = typeof event.notification.data?.url === "string" ? event.notification.data.url : "/";
  const url = requestedUrl.startsWith("/") && !requestedUrl.startsWith("//") ? new URL(requestedUrl, self.location.origin) : new URL("/", self.location.origin);
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
