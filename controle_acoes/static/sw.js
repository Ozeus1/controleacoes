/* MyInvest — service worker do PWA.
   Estratégia: app financeiro = dados sempre frescos.
   - Navegações e /api/: rede primeiro; sem rede, cai no cache (páginas) ou offline.html.
   - /static/ e CDNs: stale-while-revalidate (responde do cache e atualiza por trás).
   - Páginas centrais pré-cacheadas no install, pra funcionar offline já na 1ª visita. */
var CACHE = 'myinvest-v212';
var OFFLINE_URL = '/offline.html';

// Essenciais (públicos, sempre existem) vão com addAll — se um falhar,
// falha a instalação toda, o que é correto: são a base do offline.html.
// Páginas autenticadas (/resumo, /acoes) vão uma a uma e sem exigir
// sucesso: se o usuário instala o PWA antes de logar, ou está sem rede
// no momento da instalação, essas chamadas 401/erro não podem derrubar
// o cache dos essenciais.
var ESSENCIAIS = [
  OFFLINE_URL,
  '/static/css/style.css',
  '/static/img/investimento.png',
  '/static/img/icon-192.png',
  '/static/js/mychart.js?v=2',
  '/static/js/ticker_browser.js?v=2'
];
var PRE_CACHE_OPCIONAL = ['/resumo', '/acoes'];

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) {
      return c.addAll(ESSENCIAIS).then(function () {
        return Promise.all(PRE_CACHE_OPCIONAL.map(function (url) {
          return fetch(url).then(function (resp) {
            if (resp && resp.ok) return c.put(url, resp);
          }).catch(function () {});
        }));
      });
    })
    // Sem skipWaiting aqui: o SW novo fica "waiting" até a página pedir
    // ativação (via updatefound → banner "Nova versão" → clicar recarrega).
    // Trocar o controlador sem avisar deixava abas abertas com HTML antigo
    // sendo servidas por JS novo — inconsistência silenciosa.
  );
});

self.addEventListener('message', function (e) {
  if (e.data === 'SKIP_WAITING') self.skipWaiting();
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
