/* Service worker: o site e cada prova abertas ficam guardados no aparelho e passam a funcionar sem internet.
   - dados/enem_ANO.js: cache primeiro (arquivo imutável por versão), atualiza em segundo plano.
   - página e demais arquivos: rede primeiro, com cache de reserva (para a pessoa receber atualizações). */
const VERSAO = "correcao-enem-v4";
self.addEventListener("install", e => { self.skipWaiting(); });
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSAO).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const req = e.request; if (req.method !== "GET") return;
  const url = new URL(req.url); if (url.origin !== location.origin) return;
  if (url.pathname.includes("/dados/")) {
    e.respondWith(caches.open(VERSAO).then(async c => {
      const hit = await c.match(req);
      const rede = fetch(req).then(r => { if (r.ok) c.put(req, r.clone()); return r; }).catch(() => hit);
      return hit || rede;
    }));
  } else {
    e.respondWith(fetch(req).then(r => { const cp = r.clone(); if (r.ok) caches.open(VERSAO).then(c => c.put(req, cp)); return r; })
      .catch(() => caches.match(req).then(h => h || caches.match("./"))));
  }
});
