// Rede primeiro; se estiver sem internet, usa a última cópia salva.
const CACHE = "painel-v3";
self.addEventListener("install", e => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  // Bibliotecas do Firebase têm versão no endereço: usa a cópia salva para abrir rápido (e o login voltar logo)
  if (req.url.startsWith("https://www.gstatic.com/firebasejs/")) {
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
      return res;
    })));
    return;
  }
  e.respondWith(
    fetch(req, { cache: "no-store" }).then(res => {
      if (res.ok && (new URL(req.url).origin === location.origin || req.url.startsWith("https://fonts."))) {
        const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy));
      }
      return res;
    }).catch(() => caches.match(req, { ignoreSearch: true }))
  );
});
