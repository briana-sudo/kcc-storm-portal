// TEMPEST service worker — exists so Chrome treats the portal as an installable app
// (shows the address-bar Install option + uses the manifest icons). NETWORK-FIRST by
// design: online you always get fresh HTML/JS/data; the cache is only an offline
// fallback. POST requests (the proxy / data writes) and third-party calls (NWS, IEM,
// Census, map tiles) are never cached, so there is no stale-data risk.
const SHELL = "tempest-shell-v1";
const PRECACHE = ["./", "./index.html", "./favicon.svg", "./favicon.ico",
  "./icon-192.png", "./icon-512.png", "./apple-touch-icon.png"];

self.addEventListener("install", e => {
  self.skipWaiting();
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(PRECACHE).catch(() => {})));
});

self.addEventListener("activate", e => {
  e.waitUntil(Promise.all([
    caches.keys().then(ks => Promise.all(ks.map(k => k === SHELL ? null : caches.delete(k)))),
    self.clients.claim()
  ]));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;                       // proxy/data POSTs -> network, never cached
  let url; try { url = new URL(req.url); } catch (_) { return; }
  if (url.origin !== self.location.origin) return;        // NWS/IEM/proxy/tiles -> network, no cache
  if (req.mode === "navigate") {                          // app shell: network-first, cache only when offline
    e.respondWith(
      fetch(req).then(r => { const cp = r.clone(); caches.open(SHELL).then(c => c.put("./index.html", cp)); return r; })
        .catch(() => caches.match("./index.html").then(m => m || caches.match("./")))
    );
    return;
  }
  if (/\.(png|svg|ico|webmanifest|css)$/.test(url.pathname)) {   // static assets: cache-first (they don't change)
    e.respondWith(caches.match(req).then(m => m || fetch(req).then(r => {
      const cp = r.clone(); caches.open(SHELL).then(c => c.put(req, cp)); return r; })));
    return;
  }
  e.respondWith(fetch(req).catch(() => caches.match(req)));      // same-origin JS/etc: network-first
});

// ── PUSH (intraday alert, rich tappable layer) ──────────────────────────────
// iOS-CRITICAL: ALWAYS call showNotification inside event.waitUntil. If a push arrives without
// a shown notification, iOS cancels the subscription — so we show one even if the payload is empty.
self.addEventListener("push", e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = {}; }
  const title = d.title || "KCC hail alert";
  const body = d.body || "A storm hit in-market. Tap to review.";
  const url = d.url || "./";
  e.waitUntil(
    self.registration.showNotification(title, {
      body, data: { url }, tag: "kcc-intraday", renotify: true,
      icon: "./icon-192.png", badge: "./icon-192.png", requireInteraction: true
    })
  );
});

// tapping the notification deep-links into the approve screen (focus an open tab, else open one)
self.addEventListener("notificationclick", e => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "./";
  e.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then(wins => {
      for (const w of wins) { if ("focus" in w) { w.navigate && w.navigate(url); return w.focus(); } }
      return clients.openWindow(url);
    })
  );
});
