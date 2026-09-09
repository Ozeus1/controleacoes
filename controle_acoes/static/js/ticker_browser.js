/**
 * TickerBrowser — card embutido com um iframe da página de gráfico completo
 * (acoes.receberbemevinhos.com.br), no lugar do MyChart. Um botão expande a
 * mesma URL numa aba/página nova.
 * Uso: TickerBrowser.open(ticker)
 */
(function(global) {
'use strict';

var _modal = null;
var _iframe = null;
var _titleEl = null;

// O sufixo "?num=NNNNNN" evita a tela de login do site (a página exige
// login e o cookie de sessão dela não é enviado dentro de um iframe de
// outra origem — ver commit anterior). O número vem da meta tag
// "receberbem-num", configurável em Configuração > Gráfico Completo,
// porque esse valor muda periodicamente do lado deles.
function receberbemNum() {
    var m = document.querySelector('meta[name="receberbem-num"]');
    return m ? (m.content || '').trim() : '';
}
function url(ticker) {
    var tk = (ticker || '').toUpperCase().trim();
    if (!tk) return null;
    var u = 'https://acoes.receberbemevinhos.com.br/?action=ticker&view=' + encodeURIComponent(tk);
    var num = receberbemNum();
    if (num) u += '?num=' + encodeURIComponent(num);
    return u;
}

function ensureModal() {
    if (_modal) return;

    _modal = document.createElement('div');
    _modal.id = 'tkb-modal';
    _modal.style.cssText = 'display:none;position:fixed;inset:0;z-index:19000;'
        + 'background:rgba(0,0,0,.82);align-items:flex-start;justify-content:center;'
        + 'overflow-y:auto;padding:1.5vh 0;';

    var card = document.createElement('div');
    card.style.cssText = 'background:#0f172a;border-radius:10px;width:min(98vw,1200px);'
        + 'height:90vh;display:flex;flex-direction:column;margin:auto;'
        + 'border:1px solid #1e293b;overflow:hidden;';

    var hdr = document.createElement('div');
    hdr.style.cssText = 'display:flex;justify-content:space-between;align-items:center;'
        + 'padding:.7rem 1rem;background:#0f172a;border-bottom:1px solid #1e293b;flex-wrap:wrap;gap:.5rem;';
    hdr.innerHTML =
        '<span id="tkb-title" style="font-weight:700;font-size:1rem;color:#f1f5f9"></span>'
        + '<div style="display:flex;align-items:center;gap:.5rem;">'
        + '<button id="tkb-expand-btn" title="Abrir em página nova" style="'
        + 'padding:.2rem .55rem;border-radius:4px;font-size:.88rem;cursor:pointer;'
        + 'border:none;background:#1e293b;color:#94a3b8;">⛶</button>'
        + '<button id="tkb-close-btn" style="background:none;border:none;font-size:1.4rem;'
        + 'color:#94a3b8;cursor:pointer;line-height:1;">&times;</button>'
        + '</div>';
    card.appendChild(hdr);
    _titleEl = hdr.querySelector('#tkb-title');

    var iwrap = document.createElement('div');
    iwrap.style.cssText = 'flex:1;background:#0f172a;position:relative;';
    _iframe = document.createElement('iframe');
    _iframe.id = 'tkb-iframe';
    _iframe.style.cssText = 'width:100%;height:100%;border:none;display:block;';
    _iframe.setAttribute('referrerpolicy', 'no-referrer');
    iwrap.appendChild(_iframe);
    card.appendChild(iwrap);

    _modal.appendChild(card);
    document.body.appendChild(_modal);

    hdr.querySelector('#tkb-close-btn').onclick = function() { TickerBrowser._close(); };
    hdr.querySelector('#tkb-expand-btn').onclick = function() {
        var u = _iframe.getAttribute('data-url');
        if (u) window.open(u, '_blank', 'noopener');
    };
    _modal.addEventListener('click', function(e) { if (e.target === _modal) TickerBrowser._close(); });
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && _modal.style.display !== 'none') TickerBrowser._close();
    });
}

var TickerBrowser = {};

TickerBrowser.open = function(ticker) {
    var u = url(ticker);
    if (!u) return;
    ensureModal();
    _titleEl.textContent = (ticker || '').toUpperCase();
    _iframe.setAttribute('data-url', u);
    _iframe.src = u;
    _modal.style.display = 'flex';
};

TickerBrowser._close = function() {
    if (_modal) _modal.style.display = 'none';
    if (_iframe) _iframe.src = 'about:blank';
};

global.TickerBrowser = TickerBrowser;

})(window);
