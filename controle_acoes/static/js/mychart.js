/**
 * MyChart — candlestick com MM 8/20/200, pan/zoom, linhas de tendência persistentes.
 * Uso: MyChart.open(ticker)
 */
(function(global) {
'use strict';

// ── Estado global ──────────────────────────────────────────────────────────────
var _cache      = {};    // {TICKER: {ts, candles[]}}
var _lines      = {};    // {TICKER: [{id,x1,y1,x2,y2,color,width},...]}
var _state      = null;
var _modal      = null;
var _canvas     = null;
var _ctx        = null;
var CSRF        = '';
var _rafPending = false;
var MyChart     = {};

// ── fetch com credenciais ──────────────────────────────────────────────────────
function _fetch(url, opts) {
    opts = opts || {};
    opts.credentials = 'same-origin';
    return fetch(url, opts).then(function(r) {
        if (r.redirected && r.url.indexOf('/login') >= 0)
            throw new Error('Sessão expirada — faça login novamente');
        return r;
    });
}

// ── Utilitários ────────────────────────────────────────────────────────────────
function sma(arr, n) {
    var out = new Array(arr.length).fill(null);
    for (var i = n - 1; i < arr.length; i++) {
        var s = 0;
        for (var j = 0; j < n; j++) s += arr[i - j];
        out[i] = s / n;
    }
    return out;
}

function fmtDate(s) {
    if (!s) return '';
    var p = s.split('-');
    return p[2] + '/' + p[1] + '/' + p[0].slice(2);
}

function fmtPrice(v) {
    return parseFloat(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ── Estilos de botão ──────────────────────────────────────────────────────────
function btnStyle(active) {
    return 'padding:.2rem .55rem;border-radius:4px;font-size:.78rem;cursor:pointer;border:none;'
        + 'background:' + (active ? '#3b82f6' : '#1e293b') + ';'
        + 'color:'      + (active ? '#fff'    : '#94a3b8') + ';'
        + 'font-weight:'+ (active ? '600'     : '400')     + ';';
}
function toolBtn(active) {
    return 'padding:.2rem .55rem;border-radius:4px;font-size:.88rem;cursor:pointer;border:none;'
        + 'background:' + (active ? '#3b82f6' : '#1e293b') + ';'
        + 'color:'      + (active ? '#fff'    : '#94a3b8') + ';';
}

// ── Ferramenta ────────────────────────────────────────────────────────────────
var _tool      = 'cursor';
var _drawing   = null;
var _selLine   = null;   // linha selecionada { line, idx }
var _editDrag  = null;   // arraste de edição { mode:'p1'|'p2'|'move', ox,oy,ox1,oy1,ox2,oy2 }
var HIT_R      = 8;      // px CSS — raio de hit para extremidades

function _setTool(t) {
    _tool    = t;
    _drawing = null;
    var cur  = document.getElementById('mc-tool-cursor');
    var lin  = document.getElementById('mc-tool-line');
    if (!cur || !lin) return;
    cur.style.background = t === 'cursor' ? '#3b82f6' : '#1e293b';
    cur.style.color      = t === 'cursor' ? '#fff'    : '#94a3b8';
    lin.style.background = t === 'line'   ? '#3b82f6' : '#1e293b';
    lin.style.color      = t === 'line'   ? '#fff'    : '#94a3b8';
    _canvas.style.cursor = t === 'line' ? 'crosshair' : (t === 'pan' ? 'grab' : 'default');
}

// ── Pan / Zoom — janela deslizante sobre allCandles ───────────────────────────
// _view = { start, count, priceMin, priceMax }
// priceMin/priceMax = null → range automático a partir dos candles visíveis
var _view = null;

function _initView() {
    if (!_state || !_state.allCandles) return;
    var total = _state.allCandles.length;
    _view = { start: Math.max(0, total - _visCount()), count: _visCount(),
              priceMin: null, priceMax: null };
}

function _visCount() {
    // Baseado no período selecionado
    var per  = _state ? (_state.period || '8mo') : '8mo';
    var days = { '1mo': 22, '3mo': 63, '6mo': 130, '8mo': 174 };
    return days[per] || 174;
}

function _clampView() {
    if (!_view || !_state || !_state.allCandles) return;
    var total = _state.allCandles.length;
    _view.count = Math.max(10, Math.min(total, _view.count));
    // Permite pan além do fim: mínimo 1 candle visível à direita
    _view.start = Math.max(0, Math.min(total - 1, _view.start));
}

function _applyView() {
    if (!_state || !_state.allCandles || !_view) return;
    var all    = _state.allCandles;
    var start  = _view.start;
    var count  = _view.count;

    // Para MM200 precisamos warm-up de 200 candles antes da janela visível
    var warmup  = 200;
    var wStart  = Math.max(0, start - warmup);
    // Fatia apenas candles reais (start pode ser próximo do fim — há espaço vazio à direita)
    var visEnd  = Math.min(all.length, start + count);
    var full    = all.slice(wStart, visEnd);
    var closes  = full.map(function(c) { return c.c; });

    var ma8f   = sma(closes, 8);
    var ma20f  = sma(closes, 20);
    var ma200f = sma(closes, 200);

    var offset = start - wStart;   // índice dentro de full onde começa a janela visível
    _state._vis   = full.slice(offset);
    _state._ma8   = ma8f.slice(offset);
    _state._ma20  = ma20f.slice(offset);
    _state._ma200 = ma200f.slice(offset);
    // Quantos slots reais existem na janela (pode ser < count quando pan além do fim)
    _state._visCount = count;
}

// alias antigo usado em outros lugares
function _applyPeriod() {
    _initView();
    _applyView();
}

// ── Coordenadas CSS ↔ data/price ──────────────────────────────────────────────
// Todas as coordenadas de interação são em pixels CSS (não multiplicados por dpr)

function _cssCoords(e) {
    var rect = _canvas.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
}

function _css2data(cx, cy) {
    if (!_state || !_state._layout) return null;
    var l    = _state._layout;
    var slots = (_state._visCount || 1) - 1 || 1;
    var i    = Math.round((cx - l.padL) / l.cW * slots);
    i = Math.max(0, Math.min(_state._vis.length - 1, i));
    var price = l.priceMax - (cy - l.padT) / l.cH * (l.priceMax - l.priceMin);
    var date  = _state._vis[i] ? _state._vis[i].t : null;
    return { i: i, date: date, price: price };
}

function _data2px(date, price) {
    if (!_state || !_state._layout) return { x: 0, y: 0 };
    var l     = _state._layout;
    var vis   = _state._vis;
    var slots = (_state._visCount || 1) - 1 || 1;
    var idx   = 0;
    for (var i = 0; i < vis.length; i++) {
        if (vis[i].t <= date) idx = i;
        else break;
    }
    var x = l.padL + (idx / slots) * l.cW;
    var y = l.padT + (l.priceMax - price) / (l.priceMax - l.priceMin) * l.cH;
    return { x: x, y: y };
}

// ── Hit-test de linhas ────────────────────────────────────────────────────────
function _distPointSeg(px, py, ax, ay, bx, by) {
    var dx = bx - ax, dy = by - ay;
    var lenSq = dx*dx + dy*dy;
    if (lenSq === 0) return Math.sqrt((px-ax)*(px-ax)+(py-ay)*(py-ay));
    var t = ((px-ax)*dx + (py-ay)*dy) / lenSq;
    t = Math.max(0, Math.min(1, t));
    var nx = ax + t*dx, ny = ay + t*dy;
    return Math.sqrt((px-nx)*(px-nx)+(py-ny)*(py-ny));
}

// Retorna { line, idx, mode } ou null
function _hitLine(cx, cy) {
    var lines = (_state && _lines[_state.ticker]) || [];
    for (var i = lines.length - 1; i >= 0; i--) {
        var ln = lines[i];
        var p1 = _data2px(ln.x1, ln.y1);
        var p2 = _data2px(ln.x2, ln.y2);
        // extremidade 1
        if (Math.sqrt((cx-p1.x)*(cx-p1.x)+(cy-p1.y)*(cy-p1.y)) <= HIT_R)
            return { line: ln, idx: i, mode: 'p1' };
        // extremidade 2
        if (Math.sqrt((cx-p2.x)*(cx-p2.x)+(cy-p2.y)*(cy-p2.y)) <= HIT_R)
            return { line: ln, idx: i, mode: 'p2' };
        // meio da linha
        if (_distPointSeg(cx, cy, p1.x, p1.y, p2.x, p2.y) <= HIT_R)
            return { line: ln, idx: i, mode: 'move' };
    }
    return null;
}

function _saveLine(line) {
    _fetch('/api/chart_lines/' + _state.ticker, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body: JSON.stringify(line)
    }).then(function(r) { return r.json(); }).then(function(res) {
        line.id = res.id;
        _draw();
    });
}

function _updateLine(line) {
    if (!line.id) return;
    _fetch('/api/chart_lines/' + _state.ticker + '?id=' + line.id, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body: JSON.stringify(line)
    });
}

function _deleteLine(line) {
    if (!line.id) return;
    _fetch('/api/chart_lines/' + _state.ticker, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body: JSON.stringify({ id: line.id })
    });
}

// ── Interação: pan, zoom, linhas ───────────────────────────────────────────────
var _panStart = null;   // { clientX, startIndex }

function _onMouseDown(e) {
    if (!_state || !_view) return;
    var pt = _cssCoords(e);
    var d  = _css2data(pt.x, pt.y);
    if (!d) return;

    if (_tool === 'line') {
        _drawing = { x1: d.date, y1: d.price, x2: d.date, y2: d.price };
        _selLine = null;
        return;
    }

    if (_tool === 'cursor') {
        // Pan com Shift+click ou botão do meio (horizontal + vertical)
        if (e.button === 1 || e.shiftKey) {
            var l0 = _state._layout;
            _panStart = { clientX: e.clientX, clientY: e.clientY,
                          startIdx: _view.start,
                          startPMin: _view.priceMin != null ? _view.priceMin : l0 ? l0.priceMin : null,
                          startPMax: _view.priceMax != null ? _view.priceMax : l0 ? l0.priceMax : null };
            _canvas.style.cursor = 'grabbing';
            e.preventDefault();
            return;
        }

        // Hit-test nas linhas
        var hit = _hitLine(pt.x, pt.y);
        if (hit) {
            _selLine  = hit;
            var ln    = hit.line;
            var p1    = _data2px(ln.x1, ln.y1);
            var p2    = _data2px(ln.x2, ln.y2);
            _editDrag = { mode: hit.mode,
                          startX: pt.x, startY: pt.y,
                          ox1: ln.x1, oy1: ln.y1,
                          ox2: ln.x2, oy2: ln.y2,
                          opx1: p1.x, opy1: p1.y,
                          opx2: p2.x, opy2: p2.y };
            _canvas.style.cursor = hit.mode === 'move' ? 'grabbing' : 'crosshair';
            e.preventDefault();
            _draw();
            return;
        }

        // Clique fora de qualquer linha — deseleciona
        _selLine  = null;
        _editDrag = null;
        _draw();
    }
}

function _onMouseMove(e) {
    if (!_state || !_state._layout) return;
    var pt = _cssCoords(e);
    var d  = _css2data(pt.x, pt.y);

    _state._crossX = pt.x;
    _state._crossY = pt.y;
    _state._hoverD = d;
    _state._hoverE = e;

    if (_tool === 'line' && _drawing && d) {
        _drawing.x2 = d.date;
        _drawing.y2 = d.price;
    }

    // Edição de linha selecionada
    if (_editDrag && _selLine) {
        var ed  = _editDrag;
        var ln  = _selLine.line;
        var l   = _state._layout;
        var dxPx = pt.x - ed.startX;
        var dyPx = pt.y - ed.startY;

        if (ed.mode === 'p1') {
            // Move só a extremidade 1
            if (d) { ln.x1 = d.date; ln.y1 = d.price; }
        } else if (ed.mode === 'p2') {
            // Move só a extremidade 2
            if (d) { ln.x2 = d.date; ln.y2 = d.price; }
        } else {
            // Move a linha inteira — converte deslocamento px em data/preço
            var pxPerBar  = l.cW / (_view.count - 1 || 1);
            var pxPerPrice = l.cH / (l.priceMax - l.priceMin);
            var barsDelta  = Math.round(dxPx / pxPerBar);
            var priceDelta = -dyPx / pxPerPrice;

            // Encontra índices originais
            var vis = _state._vis;
            var i1  = 0, i2 = 0;
            for (var i = 0; i < vis.length; i++) {
                if (vis[i].t <= ed.ox1) i1 = i;
                if (vis[i].t <= ed.ox2) i2 = i;
            }
            var ni1 = Math.max(0, Math.min(vis.length-1, i1 + barsDelta));
            var ni2 = Math.max(0, Math.min(vis.length-1, i2 + barsDelta));
            ln.x1 = vis[ni1].t;  ln.y1 = ed.oy1 + priceDelta;
            ln.x2 = vis[ni2].t;  ln.y2 = ed.oy2 + priceDelta;
        }
    }

    // Cursor sobre linha — muda cursor
    if (_tool === 'cursor' && !_editDrag && !_panStart) {
        var h2 = _hitLine(pt.x, pt.y);
        _canvas.style.cursor = h2
            ? (h2.mode === 'move' ? 'grab' : 'crosshair')
            : 'default';
    }

    // Pan ativo
    if (_panStart) {
        var l        = _state._layout;
        // Pan horizontal
        var pxPerBar = l.cW / (_view.count - 1 || 1);
        var deltaH   = Math.round((e.clientX - _panStart.clientX) / pxPerBar);
        _view.start  = _panStart.startIdx - deltaH;
        _clampView();
        _applyView();
        // Pan vertical (só quando há range base disponível)
        if (_panStart.startPMin != null && _panStart.startPMax != null) {
            var range    = _panStart.startPMax - _panStart.startPMin;
            var deltaV   = (e.clientY - _panStart.clientY) / l.cH * range;
            _view.priceMin = _panStart.startPMin + deltaV;
            _view.priceMax = _panStart.startPMax + deltaV;
        }
    }

    if (!_rafPending) {
        _rafPending = true;
        requestAnimationFrame(function() {
            _rafPending = false;
            if (!_state) return;
            _draw();
            _updateHoverUI();
        });
    }
}

function _onMouseUp(e) {
    // Fim do pan
    if (_panStart) {
        _panStart = null;
        _canvas.style.cursor = 'default';
        return;
    }

    // Fim de edição de linha
    if (_editDrag && _selLine) {
        var ln = _selLine.line;
        _updateLine(ln);
        _editDrag = null;
        _canvas.style.cursor = 'default';
        _draw();
        return;
    }

    // Fim de desenho de nova linha
    if (!_state || !_drawing) return;
    var pt = _cssCoords(e);
    var d  = _css2data(pt.x, pt.y);
    if (!d) { _drawing = null; return; }

    _drawing.x2 = d.date;
    _drawing.y2 = d.price;

    var p1 = _data2px(_drawing.x1, _drawing.y1);
    var p2 = _data2px(_drawing.x2, _drawing.y2);
    if (Math.abs(p2.x - p1.x) < 4 && Math.abs(p2.y - p1.y) < 4) {
        _drawing = null; _draw(); return;
    }

    var line = { x1: _drawing.x1, y1: _drawing.y1,
                 x2: _drawing.x2, y2: _drawing.y2,
                 color: '#3b82f6', width: 1.5 };
    _drawing = null;

    _fetch('/api/chart_lines/' + _state.ticker, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body: JSON.stringify(line)
    }).then(function(r) { return r.json(); }).then(function(res) {
        line.id = res.id;
        if (!_lines[_state.ticker]) _lines[_state.ticker] = [];
        _lines[_state.ticker].push(line);
        _draw();
    });
}

function _onWheel(e) {
    if (!_state || !_view) return;
    e.preventDefault();
    var l      = _state._layout;
    var pt     = _cssCoords(e);
    var factor = e.deltaY > 0 ? 1.12 : 0.89;

    if (e.ctrlKey) {
        // Zoom vertical — âncora no preço sob o cursor
        var curPMin = _view.priceMin != null ? _view.priceMin : l.priceMin;
        var curPMax = _view.priceMax != null ? _view.priceMax : l.priceMax;
        var range   = curPMax - curPMin;
        // Preço sob o cursor como âncora
        var anchorPrice = curPMax - (pt.y - l.padT) / l.cH * range;
        var newRange    = range * factor;
        // Mantém a proporção da âncora na tela
        var ratio = (anchorPrice - curPMin) / range;
        _view.priceMin = anchorPrice - ratio * newRange;
        _view.priceMax = anchorPrice + (1 - ratio) * newRange;
    } else {
        // Zoom horizontal — âncora no candle sob o cursor
        var anchor    = Math.round((pt.x - l.padL) / l.cW * (_view.count - 1));
        var newCount  = Math.round(_view.count * factor);
        newCount = Math.max(10, Math.min(_state.allCandles.length, newCount));
        var anchorAbs = _view.start + anchor;
        var newAnchor = Math.round(anchor * newCount / _view.count);
        _view.start = anchorAbs - newAnchor;
        _view.count = newCount;
        _clampView();
        _applyView();
    }
    _draw();
}

function _updateHoverUI() {
    var hd = _state._hoverD, he = _state._hoverE;
    if (!hd || !hd.date) {
        var ci = document.getElementById('mc-crosshair-info');
        if (ci) ci.textContent = '';
        return;
    }
    var c = _state._vis[hd.i];
    if (c) {
        var ci2 = document.getElementById('mc-crosshair-info');
        if (ci2) ci2.textContent = fmtDate(c.t)
            + '  A:' + fmtPrice(c.o) + '  H:' + fmtPrice(c.h)
            + '  L:' + fmtPrice(c.l) + '  F:' + fmtPrice(c.c);
    }
    if (_tool === 'cursor' && c) {
        var tip = document.getElementById('mc-tooltip');
        if (!tip || !he) return;
        tip.innerHTML = '<strong>' + fmtDate(c.t) + '</strong>'
            + '  A:<span style="color:#94a3b8">' + fmtPrice(c.o) + '</span>'
            + '  H:<span style="color:#4ade80">' + fmtPrice(c.h) + '</span>'
            + '  L:<span style="color:#f87171">' + fmtPrice(c.l) + '</span>'
            + '  F:<strong>' + fmtPrice(c.c) + '</strong>'
            + '  V:<span style="color:#94a3b8">'
            + (c.v >= 1e6 ? (c.v/1e6).toFixed(1)+'M' : c.v >= 1e3 ? (c.v/1e3).toFixed(0)+'k' : c.v)
            + '</span>';
        var rect = _canvas.getBoundingClientRect();
        var tx = he.clientX - rect.left + 14;
        var ty = he.clientY - rect.top  - 10;
        if (tx + 340 > rect.width) tx = he.clientX - rect.left - 350;
        tip.style.left    = tx + 'px';
        tip.style.top     = ty + 'px';
        tip.style.display = 'block';
    } else {
        var tip2 = document.getElementById('mc-tooltip');
        if (tip2) tip2.style.display = 'none';
    }
}

// ── Apagar linhas ──────────────────────────────────────────────────────────────
MyChart._delLines = function() {
    if (!_state) return;
    if (!confirm('Apagar todas as linhas de ' + _state.ticker + '?')) return;
    _fetch('/api/chart_lines/' + _state.ticker, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body: JSON.stringify({})
    }).then(function() { _lines[_state.ticker] = []; _draw(); });
};

// ── Modal ─────────────────────────────────────────────────────────────────────
function ensureModal() {
    if (_modal) return;

    var csrfMeta = document.querySelector('meta[name=csrf-token]');
    CSRF = csrfMeta ? csrfMeta.content : '';

    _modal = document.createElement('div');
    _modal.id = 'mychart-modal';
    _modal.style.cssText = 'display:none;position:fixed;inset:0;z-index:19000;'
        + 'background:rgba(0,0,0,.82);align-items:flex-start;justify-content:center;'
        + 'overflow-y:auto;padding:1.5vh 0;';

    var card = document.createElement('div');
    card.style.cssText = 'background:#0f172a;border-radius:10px;width:min(98vw,1200px);'
        + 'display:flex;flex-direction:column;margin:auto;border:1px solid #1e293b;overflow:hidden;';

    // Header
    var hdr = document.createElement('div');
    hdr.style.cssText = 'display:flex;justify-content:space-between;align-items:center;'
        + 'padding:.7rem 1rem;background:#0f172a;border-bottom:1px solid #1e293b;flex-wrap:wrap;gap:.5rem;';
    hdr.innerHTML =
        '<div style="display:flex;align-items:center;gap:.75rem;flex-wrap:wrap">'
        + '<span id="mc-title" style="font-weight:700;font-size:1rem;color:#f1f5f9"></span>'
        + '<span id="mc-price" style="font-size:1.1rem;font-weight:700;color:#f1f5f9"></span>'
        + '<span id="mc-change" style="font-size:.85rem"></span>'
        + '</div>'
        + '<div style="display:flex;align-items:center;gap:.5rem;flex-wrap:wrap">'
        + '<span style="font-size:.78rem;color:#64748b">Período:</span>'
        + '<button class="mc-per-btn" data-per="1mo" style="' + btnStyle()       + '">1M</button>'
        + '<button class="mc-per-btn" data-per="3mo" style="' + btnStyle()       + '">3M</button>'
        + '<button class="mc-per-btn" data-per="6mo" style="' + btnStyle()       + '">6M</button>'
        + '<button class="mc-per-btn" data-per="8mo" style="' + btnStyle(true)   + '">8M</button>'
        + '<span style="width:1px;height:16px;background:#334155;margin:0 .25rem"></span>'
        + '<span style="font-size:.78rem;color:#64748b">Ferramenta:</span>'
        + '<button id="mc-tool-cursor" title="Cursor (pan com Shift+drag)"  style="' + toolBtn(true)  + '">↖</button>'
        + '<button id="mc-tool-line"   title="Linha (L)"                    style="' + toolBtn(false) + '">╱</button>'
        + '<button id="mc-del-lines"   title="Apagar linhas"                style="' + toolBtn(false) + '" onclick="MyChart._delLines()">🗑</button>'
        + '<span style="width:1px;height:16px;background:#334155;margin:0 .25rem"></span>'
        + '<button onclick="MyChart._close()" style="background:none;border:none;font-size:1.4rem;color:#94a3b8;cursor:pointer;line-height:1;">&times;</button>'
        + '</div>';
    card.appendChild(hdr);

    // MA toolbar
    var maRow = document.createElement('div');
    maRow.style.cssText = 'display:flex;gap:.5rem;align-items:center;padding:.4rem 1rem;'
        + 'background:#0f172a;border-bottom:1px solid #1e293b;flex-wrap:wrap;';
    maRow.innerHTML =
        '<span style="font-size:.75rem;color:#64748b">Médias:</span>'
        + '<label style="font-size:.75rem;cursor:pointer;color:#fbbf24"><input type="checkbox" id="mc-ma8"   checked style="margin-right:.3rem">MM8</label>'
        + '<label style="font-size:.75rem;cursor:pointer;color:#60a5fa"><input type="checkbox" id="mc-ma20"  checked style="margin-right:.3rem">MM20</label>'
        + '<label style="font-size:.75rem;cursor:pointer;color:#f87171"><input type="checkbox" id="mc-ma200" checked style="margin-right:.3rem">MM200</label>'
        + '<span style="font-size:.72rem;color:#475569;margin-left:.5rem">🖱 scroll=zoom  Shift+drag=pan</span>'
        + '<span id="mc-crosshair-info" style="font-size:.75rem;color:#94a3b8;margin-left:auto"></span>';
    card.appendChild(maRow);

    // Canvas
    var cwrap = document.createElement('div');
    cwrap.style.cssText = 'position:relative;width:100%;background:#0f172a;';
    cwrap.id = 'mc-canvas-wrap';
    _canvas = document.createElement('canvas');
    _canvas.id = 'mc-canvas';
    _canvas.style.cssText = 'display:block;width:100%;cursor:default;';
    cwrap.appendChild(_canvas);

    var tooltip = document.createElement('div');
    tooltip.id = 'mc-tooltip';
    tooltip.style.cssText = 'display:none;position:absolute;background:#1e293b;border:1px solid #334155;'
        + 'border-radius:6px;padding:.4rem .7rem;font-size:.78rem;pointer-events:none;z-index:10;'
        + 'white-space:nowrap;color:#e2e8f0;';
    cwrap.appendChild(tooltip);

    // Volume
    var vcwrap = document.createElement('div');
    vcwrap.style.cssText = 'width:100%;background:#0f172a;border-top:1px solid #1e293b;';
    var vcvs = document.createElement('canvas');
    vcvs.id = 'mc-vol-canvas';
    vcvs.style.cssText = 'display:block;width:100%;';
    vcwrap.appendChild(vcvs);

    card.appendChild(cwrap);
    card.appendChild(vcwrap);

    // Status
    var sbar = document.createElement('div');
    sbar.id = 'mc-status';
    sbar.style.cssText = 'padding:.35rem 1rem;font-size:.75rem;color:#64748b;border-top:1px solid #1e293b;background:#0f172a;min-height:28px;';
    card.appendChild(sbar);

    _modal.appendChild(card);
    document.body.appendChild(_modal);
    _ctx = _canvas.getContext('2d');

    // Eventos modal
    _modal.addEventListener('click', function(e) { if (e.target === _modal) MyChart._close(); });
    document.addEventListener('keydown', function(e) {
        if (_modal.style.display === 'none') return;
        if (e.key === 'Escape') {
            if (_selLine) { _selLine = null; _editDrag = null; _draw(); }
            else MyChart._close();
            return;
        }
        if (e.key === 'l' || e.key === 'L') { _setTool('line'); return; }
        if (e.key === 'c' || e.key === 'C') { _setTool('cursor'); return; }
        if ((e.key === 'Delete' || e.key === 'Backspace') && _selLine) {
            e.preventDefault();
            var ln  = _selLine.line;
            var idx = _selLine.idx;
            _deleteLine(ln);
            var arr = _lines[_state.ticker];
            if (arr) arr.splice(idx, 1);
            _selLine  = null;
            _editDrag = null;
            _draw();
        }
    });

    // Botões período
    _modal.querySelectorAll('.mc-per-btn').forEach(function(b) {
        b.onclick = function() {
            _modal.querySelectorAll('.mc-per-btn').forEach(function(x) {
                x.style.background = '#1e293b'; x.style.color = '#94a3b8'; x.style.fontWeight = '400';
            });
            b.style.background = '#3b82f6'; b.style.color = '#fff'; b.style.fontWeight = '600';
            if (_state) { _state.period = b.dataset.per; _applyPeriod(); _draw(); }
        };
    });

    // Botões ferramenta
    document.getElementById('mc-tool-cursor').onclick = function() { _setTool('cursor'); };
    document.getElementById('mc-tool-line').onclick   = function() { _setTool('line'); };

    // MA checkboxes
    ['mc-ma8','mc-ma20','mc-ma200'].forEach(function(id) {
        document.getElementById(id).onchange = function() { if (_state) _draw(); };
    });

    // Resize
    window.addEventListener('resize', function() {
        if (_state && _modal.style.display !== 'none') { _resize(); _draw(); }
    });

    // Eventos canvas
    _canvas.addEventListener('mousedown',  _onMouseDown);
    _canvas.addEventListener('mousemove',  _onMouseMove);
    _canvas.addEventListener('mouseup',    _onMouseUp);
    _canvas.addEventListener('wheel',      _onWheel, { passive: false });
    _canvas.addEventListener('dblclick',   function() {
        if (!_view) return;
        _view.priceMin = null;
        _view.priceMax = null;
        _draw();
    });
    _canvas.addEventListener('mouseleave', function() {
        _panStart = null;
        var tip = document.getElementById('mc-tooltip');
        if (tip) tip.style.display = 'none';
        var ci = document.getElementById('mc-crosshair-info');
        if (ci) ci.textContent = '';
        if (_state) { _state._crossX = null; _draw(); }
    });
    _canvas.addEventListener('contextmenu', function(e) { e.preventDefault(); });
}

// ── Abertura ──────────────────────────────────────────────────────────────────
MyChart.open = function(ticker, isIntl) {
    ticker = (ticker || '').toUpperCase().trim();
    var yfticker = ticker;
    if (!isIntl && /^[A-Z]{4}[0-9]/.test(ticker) && ticker.indexOf('.') < 0)
        yfticker = ticker + '.SA';

    ensureModal();
    _modal.style.display = 'flex';
    document.getElementById('mc-title').textContent  = '📈 ' + ticker;
    document.getElementById('mc-price').textContent  = '';
    document.getElementById('mc-change').textContent = '';
    document.getElementById('mc-status').textContent = '⏳ Carregando dados…';

    _state = { ticker: ticker, yfticker: yfticker, period: '8mo',
               _vis: [], _layout: null, _crossX: null, _crossY: null };
    _view  = null;
    _setTool('cursor');
    _resize();

    // Linhas salvas
    if (!_lines[ticker]) {
        _fetch('/api/chart_lines/' + ticker)
            .then(function(r) { return r.json(); })
            .then(function(d) {
                _lines[ticker] = Array.isArray(d) ? d : [];
                if (_state && _state.ticker === ticker) _draw();
            });
    }

    // Cache cliente 2 min
    var now = Date.now(), cached = _cache[ticker];
    if (cached && (now - cached.ts) < 120000) {
        _state.allCandles = cached.candles;
        _applyPeriod(); _draw();
        return;
    }

    var url = '/api/chart_data/' + encodeURIComponent(ticker);
    var existing = cached ? cached.candles : null;
    if (existing && existing.length)
        url += '?since=' + existing[existing.length - 1].t;

    _fetch(url)
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.error) { document.getElementById('mc-status').textContent = '✗ ' + d.error; return; }
            var candles = d.candles;
            if (existing && existing.length && candles.length) {
                var nd = {};
                candles.forEach(function(c) { nd[c.t] = true; });
                candles = existing.filter(function(c) { return !nd[c.t]; }).concat(candles);
                candles.sort(function(a, b) { return a.t < b.t ? -1 : 1; });
            }
            _cache[ticker] = { ts: Date.now(), candles: candles };
            if (_state && _state.ticker === ticker) {
                _state.allCandles = candles;
                _applyPeriod(); _draw();
            }
        })
        .catch(function(e) {
            document.getElementById('mc-status').textContent = '✗ Erro: ' + e;
        });
};

MyChart._close = function() {
    if (_modal) _modal.style.display = 'none';
    _state = null; _view = null;
};

// ── Resize canvas ──────────────────────────────────────────────────────────────
function _resize() {
    if (!_canvas) return;
    var dpr  = window.devicePixelRatio || 1;
    var wrap = document.getElementById('mc-canvas-wrap');
    if (!wrap) return;
    var W = wrap.clientWidth || 900;
    var H = Math.max(380, Math.round(W * 0.44));
    _canvas.width        = W * dpr;
    _canvas.height       = H * dpr;
    _canvas.style.height = H + 'px';
    _ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    var vcvs = document.getElementById('mc-vol-canvas');
    if (vcvs) {
        var VH = Math.round(H * 0.15);
        vcvs.width        = W * dpr;
        vcvs.height       = VH * dpr;
        vcvs.style.height = VH + 'px';
        vcvs.getContext('2d').setTransform(dpr, 0, 0, dpr, 0, 0);
    }
}

// ── Desenho ───────────────────────────────────────────────────────────────────
var PAD = { T: 32, R: 72, B: 28, L: 12 };

function _draw() {
    if (!_state || !_state._vis || !_state._vis.length) return;
    var vis  = _state._vis;
    var dpr  = window.devicePixelRatio || 1;
    var W    = _canvas.width  / dpr;
    var H    = _canvas.height / dpr;
    var ctx  = _ctx;

    ctx.clearRect(0, 0, W, H);

    var padL = PAD.L, padR = PAD.R, padT = PAD.T, padB = PAD.B;
    var cW   = W - padL - padR;
    var cH   = H - padT - padB;

    // Preço range — manual (pan/zoom vertical) ou automático
    var priceMin, priceMax;
    if (_view && _view.priceMin != null && _view.priceMax != null) {
        priceMin = _view.priceMin;
        priceMax = _view.priceMax;
    } else {
        priceMin = Infinity; priceMax = -Infinity;
        for (var i = 0; i < vis.length; i++) {
            if (vis[i].l < priceMin) priceMin = vis[i].l;
            if (vis[i].h > priceMax) priceMax = vis[i].h;
        }
        var pad5 = (priceMax - priceMin) * 0.05 || priceMax * 0.01;
        priceMin -= pad5; priceMax += pad5;
    }

    // Layout em pixels CSS (usado por _css2data e _data2px)
    _state._layout = { padL: padL, padR: padR, padT: padT, padB: padB,
                       cW: cW, cH: cH, priceMin: priceMin, priceMax: priceMax };

    // slots = nº de posições na janela (inclui espaço vazio à direita quando pan além do fim)
    var slots = (_state._visCount || vis.length) - 1 || 1;
    function xPx(i) { return padL + (i / slots) * cW; }
    function yPx(p) { return padT + (1 - (p - priceMin) / (priceMax - priceMin)) * cH; }

    // Fundo
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, W, H);

    // Grade horizontal
    ctx.strokeStyle = 'rgba(51,65,85,.5)'; ctx.lineWidth = 1;
    for (var i = 0; i <= 6; i++) {
        var yg = padT + i * cH / 6;
        ctx.beginPath(); ctx.moveTo(padL, yg); ctx.lineTo(W - padR, yg); ctx.stroke();
        var pL2 = priceMax - i * (priceMax - priceMin) / 6;
        ctx.fillStyle = '#64748b'; ctx.font = '10px Inter,sans-serif'; ctx.textAlign = 'left';
        ctx.fillText(fmtPrice(pL2), W - padR + 4, yg + 4);
    }

    // Grade vertical
    var dateStep = Math.max(1, Math.floor(vis.length / 8));   // rótulos só sobre candles reais
    ctx.fillStyle = '#64748b'; ctx.font = '10px Inter,sans-serif'; ctx.textAlign = 'center';
    for (var i = 0; i < vis.length; i += dateStep) {
        var xg = xPx(i);
        ctx.strokeStyle = 'rgba(51,65,85,.35)'; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(xg, padT); ctx.lineTo(xg, H - padB); ctx.stroke();
        ctx.fillText(fmtDate(vis[i].t), xg, H - padB + 14);
    }

    // MAs
    var showMA8   = document.getElementById('mc-ma8')   && document.getElementById('mc-ma8').checked;
    var showMA20  = document.getElementById('mc-ma20')  && document.getElementById('mc-ma20').checked;
    var showMA200 = document.getElementById('mc-ma200') && document.getElementById('mc-ma200').checked;

    function drawMA(arr, color, lw) {
        if (!arr || !arr.length) return;
        ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.setLineDash([]);
        ctx.beginPath(); var started = false;
        for (var i = 0; i < arr.length; i++) {
            if (arr[i] == null) { started = false; continue; }
            var x = xPx(i), y = yPx(arr[i]);
            if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
        }
        ctx.stroke();
    }

    if (showMA200) drawMA(_state._ma200, '#f87171', 1.2);
    if (showMA20)  drawMA(_state._ma20,  '#60a5fa', 1.2);
    if (showMA8)   drawMA(_state._ma8,   '#fbbf24', 1.0);

    // Candles
    var candleW = Math.max(1, Math.min(14, cW / (slots + 1) * 0.7));
    for (var i = 0; i < vis.length; i++) {
        var c    = vis[i];
        var bull = c.c >= c.o;
        var col  = bull ? '#26a69a' : '#ef5350';
        var xc   = xPx(i);
        ctx.strokeStyle = col; ctx.lineWidth = 1; ctx.setLineDash([]);
        ctx.beginPath(); ctx.moveTo(xc, yPx(c.h)); ctx.lineTo(xc, yPx(c.l)); ctx.stroke();
        ctx.fillStyle = col;
        ctx.fillRect(xc - candleW/2, Math.min(yPx(c.o), yPx(c.c)),
                     candleW, Math.max(1, Math.abs(yPx(c.c) - yPx(c.o))));
    }

    // Linhas de tendência salvas
    (_lines[_state.ticker] || []).forEach(function(ln, idx) {
        var p1  = _data2px(ln.x1, ln.y1), p2 = _data2px(ln.x2, ln.y2);
        var sel = _selLine && _selLine.idx === idx;
        ctx.strokeStyle = sel ? '#facc15' : (ln.color || '#3b82f6');
        ctx.lineWidth   = sel ? 2.5 : (ln.width || 1.5);
        ctx.setLineDash([]);
        ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.stroke();
        // Extremidades
        ctx.fillStyle = sel ? '#facc15' : (ln.color || '#3b82f6');
        ctx.beginPath(); ctx.arc(p1.x, p1.y, sel ? 5 : 3, 0, 2*Math.PI); ctx.fill();
        ctx.beginPath(); ctx.arc(p2.x, p2.y, sel ? 5 : 3, 0, 2*Math.PI); ctx.fill();
        // Label de instrução quando selecionada
        if (sel) {
            var mx = (p1.x + p2.x) / 2, my = (p1.y + p2.y) / 2 - 10;
            ctx.fillStyle = 'rgba(30,41,59,.85)';
            ctx.fillRect(mx - 82, my - 12, 164, 18);
            ctx.fillStyle = '#facc15'; ctx.font = '10px Inter,sans-serif'; ctx.textAlign = 'center';
            ctx.fillText('arrastar=mover  ○=redimensionar  Del=excluir', mx, my);
        }
    });

    // Linha sendo desenhada
    if (_drawing) {
        var p1 = _data2px(_drawing.x1, _drawing.y1);
        var p2 = _data2px(_drawing.x2, _drawing.y2);
        ctx.strokeStyle = '#fbbf24'; ctx.lineWidth = 1.5; ctx.setLineDash([4, 3]);
        ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.stroke();
        ctx.setLineDash([]);
    }

    // Crosshair
    if (_state._crossX != null) {
        var cx = _state._crossX, cy = _state._crossY;
        ctx.strokeStyle = 'rgba(148,163,184,.45)'; ctx.lineWidth = 1; ctx.setLineDash([3, 3]);
        ctx.beginPath(); ctx.moveTo(cx, padT); ctx.lineTo(cx, H - padB); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(padL, cy);  ctx.lineTo(W - padR, cy); ctx.stroke();
        ctx.setLineDash([]);
        var pCross = priceMax - (cy - padT) / cH * (priceMax - priceMin);
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(W - padR + 1, cy - 9, padR - 2, 18);
        ctx.fillStyle = '#e2e8f0'; ctx.font = 'bold 10px Inter,sans-serif'; ctx.textAlign = 'left';
        ctx.fillText(fmtPrice(pCross), W - padR + 4, cy + 4);
    }

    // Preço último
    var lastClose = vis[vis.length - 1].c;
    var yLast     = yPx(lastClose);
    var prevClose = vis.length > 1 ? vis[vis.length - 2].c : lastClose;
    var lastColor = lastClose >= prevClose ? '#26a69a' : '#ef5350';
    ctx.strokeStyle = lastColor; ctx.lineWidth = 1; ctx.setLineDash([4, 3]);
    ctx.beginPath(); ctx.moveTo(padL, yLast); ctx.lineTo(W - padR, yLast); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = lastColor;
    ctx.fillRect(W - padR + 1, yLast - 9, padR - 2, 18);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 10px Inter,sans-serif'; ctx.textAlign = 'left';
    ctx.fillText(fmtPrice(lastClose), W - padR + 4, yLast + 4);

    // Header
    var chgPct = (lastClose - prevClose) / prevClose * 100;
    document.getElementById('mc-price').textContent = 'R$ ' + fmtPrice(lastClose);
    var chgEl = document.getElementById('mc-change');
    chgEl.textContent = (chgPct >= 0 ? '+' : '') + chgPct.toFixed(2).replace('.', ',') + '%';
    chgEl.style.color = chgPct >= 0 ? '#26a69a' : '#ef5350';

    document.getElementById('mc-status').textContent =
        vis.length + ' candles  |  ' + fmtDate(vis[0].t) + ' – ' + fmtDate(vis[vis.length-1].t)
        + '  |  Scroll=zoom  Ctrl+Scroll=zoom↕  Shift+drag=pan  2×clique=reset↕  L=linha  C=cursor';

    _drawVolume(vis, W, cW);
}

function _drawVolume(vis, W, cW) {
    var vcvs = document.getElementById('mc-vol-canvas');
    if (!vcvs) return;
    var dpr  = window.devicePixelRatio || 1;
    var VW   = vcvs.width  / dpr;
    var VH   = vcvs.height / dpr;
    var ctx2 = vcvs.getContext('2d');
    ctx2.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx2.clearRect(0, 0, VW, VH);
    ctx2.fillStyle = '#0f172a'; ctx2.fillRect(0, 0, VW, VH);

    var vCW   = VW - PAD.L - PAD.R;
    var maxV  = 1;
    for (var i = 0; i < vis.length; i++) if (vis[i].v > maxV) maxV = vis[i].v;
    var vSlots = (_state._visCount || vis.length) - 1 || 1;
    var barW  = Math.max(1, vCW / (vSlots + 1) * 0.7);

    function xPxV(i) { return PAD.L + (i / vSlots) * vCW; }
    for (var i = 0; i < vis.length; i++) {
        var c  = vis[i];
        var bH = (c.v / maxV) * (VH - 4);
        ctx2.fillStyle = c.c >= c.o ? 'rgba(38,166,154,.6)' : 'rgba(239,83,80,.6)';
        ctx2.fillRect(xPxV(i) - barW/2, VH - bH, barW, bH);
    }
}

// ── Gráfico inline (Radar) ────────────────────────────────────────────────────
MyChart.openInline = function(containerId, ticker, isIntl) {
    ticker = (ticker || '').toUpperCase().trim();
    var wrap = document.getElementById(containerId);
    if (!wrap) return;
    wrap.innerHTML = '<p style="color:#94a3b8;padding:.5rem;font-size:.8rem">⏳ Carregando ' + ticker + '…</p>';

    var doRender = function(candles) {
        if (!candles || !candles.length) {
            wrap.innerHTML = '<p style="color:#f87171;padding:.5rem;font-size:.8rem">Sem dados para ' + ticker + '</p>';
            return;
        }
        var vis    = candles.slice(-63);
        var closes = vis.map(function(c) { return c.c; });
        var ma8    = sma(closes, 8), ma20 = sma(closes, 20), ma50 = sma(closes, 50);

        wrap.innerHTML = '';
        var dpr = window.devicePixelRatio || 1;
        var W = wrap.clientWidth || 420, H = 220;
        var cvs = document.createElement('canvas');
        cvs.width = W*dpr; cvs.height = H*dpr;
        cvs.style.cssText = 'display:block;width:100%;height:'+H+'px;';
        wrap.appendChild(cvs);
        var ctx = cvs.getContext('2d');
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        var pL=8,pR=52,pT=12,pB=20,cW=W-pL-pR,cH=H-pT-pB;
        var mn=Infinity,mx=-Infinity;
        for (var i=0;i<vis.length;i++){if(vis[i].l<mn)mn=vis[i].l;if(vis[i].h>mx)mx=vis[i].h;}
        var p5=(mx-mn)*.05||mx*.01; mn-=p5; mx+=p5;
        function xp(i){return pL+(i/(vis.length-1||1))*cW;}
        function yp(v){return pT+(1-(v-mn)/(mx-mn))*cH;}

        ctx.fillStyle='#0f172a'; ctx.fillRect(0,0,W,H);
        ctx.strokeStyle='rgba(51,65,85,.4)'; ctx.lineWidth=1;
        for(var g=0;g<=4;g++){
            var yg=pT+g*cH/4;
            ctx.beginPath();ctx.moveTo(pL,yg);ctx.lineTo(W-pR,yg);ctx.stroke();
            ctx.fillStyle='#64748b';ctx.font='9px Inter,sans-serif';ctx.textAlign='left';
            ctx.fillText(fmtPrice(mx-g*(mx-mn)/4),W-pR+3,yg+3);
        }
        function dMA(arr,col,lw){
            ctx.strokeStyle=col;ctx.lineWidth=lw;ctx.setLineDash([]);
            ctx.beginPath();var st=false;
            for(var i=0;i<arr.length;i++){if(arr[i]==null){st=false;continue;}
                var x=xp(i),y=yp(arr[i]);if(!st){ctx.moveTo(x,y);st=true;}else ctx.lineTo(x,y);}
            ctx.stroke();
        }
        dMA(ma50,'#f87171',1); dMA(ma20,'#60a5fa',1); dMA(ma8,'#fbbf24',.8);
        var cw2=Math.max(1,Math.min(10,cW/vis.length*.7));
        for(var i=0;i<vis.length;i++){
            var c=vis[i],bull=c.c>=c.o,col=bull?'#26a69a':'#ef5350';
            var xc=xp(i);
            ctx.strokeStyle=col;ctx.lineWidth=1;ctx.setLineDash([]);
            ctx.beginPath();ctx.moveTo(xc,yp(c.h));ctx.lineTo(xc,yp(c.l));ctx.stroke();
            ctx.fillStyle=col;
            ctx.fillRect(xc-cw2/2,Math.min(yp(c.o),yp(c.c)),cw2,Math.max(1,Math.abs(yp(c.c)-yp(c.o))));
        }
        var lc=vis[vis.length-1].c,yL=yp(lc);
        ctx.strokeStyle='#94a3b8';ctx.lineWidth=.8;ctx.setLineDash([3,3]);
        ctx.beginPath();ctx.moveTo(pL,yL);ctx.lineTo(W-pR,yL);ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle='#1e293b';ctx.fillRect(W-pR+1,yL-8,pR-2,16);
        ctx.fillStyle='#e2e8f0';ctx.font='bold 9px Inter,sans-serif';ctx.textAlign='left';
        ctx.fillText(fmtPrice(lc),W-pR+3,yL+4);
    };

    var now=Date.now(), cached=_cache[ticker];
    if(cached&&(now-cached.ts)<120000){doRender(cached.candles);return;}
    _fetch('/api/chart_data/'+encodeURIComponent(ticker))
        .then(function(r){return r.json();})
        .then(function(d){
            if(d.error){wrap.innerHTML='<p style="color:#f87171;padding:.5rem;font-size:.8rem">'+d.error+'</p>';return;}
            _cache[ticker]={ts:Date.now(),candles:d.candles};
            doRender(d.candles);
        }).catch(function(){
            wrap.innerHTML='<p style="color:#f87171;padding:.5rem;font-size:.8rem">Erro ao carregar dados</p>';
        });
};

// ── Exporta ───────────────────────────────────────────────────────────────────
global.MyChart = MyChart;

global.buildTVWidget = function(containerId, symbol) {
    var ticker = symbol.replace(/^BMFBOVESPA:/, '').replace(/\.SA$/, '');
    MyChart.open(ticker, !/^[A-Z]{4}[0-9]/.test(ticker));
};

})(window);
