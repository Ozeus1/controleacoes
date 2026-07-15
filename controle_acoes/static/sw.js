/* MyInvest — service worker do PWA.
   Estratégia: app financeiro = dados sempre frescos.
   - Navegações e /api/: rede primeiro; sem rede, cai no cache (páginas) ou offline.html.
   - /static/ e CDNs: stale-while-revalidate (responde do cache e atualiza por trás). */
var CACHE = 'myinvest-v20';
var OFFLINE_URL = '/offline.html';

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) {
      return c.addAll([
        OFFLINE_URL,
        '/static/css/style.css',
        '/static/img/investimento.png',
        '/static/img/icon-192.png'
      ]);
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        if (k !== CACHE) return caches.delete(k);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;                    // POSTs nunca passam pelo cache
  var url = new URL(req.url);

  // Dados de API: só rede (sem cache — valores de mercado não podem ficar velhos)
  if (url.pathname.indexOf('/api/') === 0) return;

  // Navegação de página: rede primeiro, cache como contingência
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req).then(function (resp) {
        var copy = resp.clone();
        caches.open(CACHE).then(function (c) { c.put(req, copy); });
        return resp;
      }).catch(function () {
        return caches.match(req).then(function (hit) {
          return hit || caches.match(OFFLINE_URL);
        });
      })
    );
    return;
  }

  // Assets (static, fonts, CDNs): stale-while-revalidate
  e.respondWith(
    caches.match(req).then(function (hit) {
      var net = fetch(req).then(function (resp) {
        if (resp && resp.status === 200 && (resp.type === 'basic' || resp.type === 'cors')) {
          var copy = resp.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
        }
        return resp;
      }).catch(function () { return hit; });
      return hit || net;
    })
  );
});
