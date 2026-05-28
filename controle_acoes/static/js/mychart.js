/**
 * MyChart — gráfico de candlestick com MM 8/20/200, linhas de tendência persistentes.
 * Uso: MyChart.open(ticker)
 */
(function(global) {
'use strict';

// ── Estado global ──────────────────────────────────────────────────────────────
var _cache    = {};   // {TICKER: {ts, candles[]}}
var _lines    = {};   // {TICKER: [{id,x1,y1,x2,y2,color,width},...]}
var _state    = null; // estado atual do gráfico aberto
var _modal    = null;
var _canvas   = null;
var _ctx      = null;
var CSRF      = '';
var _rafPending = false; // throttle RAF para mousemove

// ── Utilitários ────────────────────────────────────────────────────────────────
function sma(arr, n) {
    var out = new Array(arr.length).fill(null);
    for (var i = n - 1; i < arr.length; i++) {
        var sum = 0;
        for (var j = 0; j < n; j++) sum += arr[i - j];
        out[i] = sum / n;
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

// ── Inicialização do modal ─────────────────────────────────────────────────────
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
    card.style.cssText = 'background:#0f172a;border-radius:10px;padding:0;'
        + 'width:min(98vw,1200px);display:flex;flex-direction:column;margin:auto;'
        + 'border:1px solid #1e293b;overflow:hidden;';

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
        + '<button class="mc-per-btn" data-per="1mo"  style="' + btnStyle() + '">1M</button>'
        + '<button class="mc-per-btn" data-per="3mo"  style="' + btnStyle() + '">3M</button>'
        + '<button class="mc-per-btn" data-per="6mo"  style="' + btnStyle(true) + '">6M</button>'
        + '<span style="width:1px;height:16px;background:#334155;margin:0 .25rem"></span>'
        + '<span style="font-size:.78rem;color:#64748b">Ferramenta:</span>'
        + '<button id="mc-tool-cursor" title="Cursor"  style="' + toolBtn(true)  + '">↖</button>'
        + '<button id="mc-tool-line"   title="Linha"   style="' + toolBtn(false) + '">╱</button>'
        + '<button id="mc-del-lines"   title="Apagar linhas" style="' + toolBtn(false) + '" onclick="MyChart._delLines()">🗑</button>'
        + '<span style="width:1px;height:16px;background:#334155;margin:0 .25rem"></span>'
        + '<button onclick="MyChart._close()" style="background:none;border:none;font-size:1.4rem;'
        + 'color:#94a3b8;cursor:pointer;line-height:1;">&times;</button>'
        + '</div>';
    card.appendChild(hdr);

    // Toolbar MAs
    var maRow = document.createElement('div');
    maRow.style.cssText = 'display:flex;gap:.5rem;align-items:center;padding:.4rem 1rem;'
        + 'background:#0f172a;border-bottom:1px solid #1e293b;flex-wrap:wrap;';
    maRow.innerHTML =
        '<span style="font-size:.75rem;color:#64748b">Médias:</span>'
        + '<label style="font-size:.75rem;cursor:pointer;color:#fbbf24">'
        + '<input type="checkbox" id="mc-ma8" checked style="margin-right:.3rem">MM8</label>'
        + '<label style="font-size:.75rem;cursor:pointer;color:#60a5fa">'
        + '<input type="checkbox" id="mc-ma20" checked style="margin-right:.3rem">MM20</label>'
        + '<label style="font-size:.75rem;cursor:pointer;color:#f87171">'
        + '<input type="checkbox" id="mc-ma50" checked style="margin-right:.3rem">MM50</label>'
        + '<span id="mc-crosshair-info" style="font-size:.75rem;color:#94a3b8;margin-left:.5rem"></span>';
    card.appendChild(maRow);

    // Canvas wrap
    var cwrap = document.createElement('div');
    cwrap.style.cssText = 'position:relative;width:100%;background:#0f172a;';
    cwrap.id = 'mc-canvas-wrap';

    _canvas = document.createElement('canvas');
    _canvas.id = 'mc-canvas';
    _canvas.style.cssText = 'display:block;width:100%;cursor:crosshair;';
    cwrap.appendChild(_canvas);

    var tooltip = document.createElement('div');
    tooltip.id = 'mc-tooltip';
    tooltip.style.cssText = 'display:none;position:absolute;background:#1e293b;border:1px solid #334155;'
        + 'border-radius:6px;padding:.4rem .7rem;font-size:.78rem;pointer-events:none;z-index:10;'
        + 'white-space:nowrap;color:#e2e8f0;';
    cwrap.appendChild(tooltip);

    // Volume bar canvas
    var vcwrap = document.createElement('div');
    vcwrap.style.cssText = 'width:100%;background:#0f172a;border-top:1px solid #1e293b;';
    var vcvs = document.createElement('canvas');
    vcvs.id = 'mc-vol-canvas';
    vcvs.style.cssText = 'display:block;width:100%;';
    vcwrap.appendChild(vcvs);

    card.appendChild(cwrap);
    card.appendChild(vcwrap);

    // Status bar
    var sbar = document.createElement('div');
    sbar.id = 'mc-status';
    sbar.style.cssText = 'padding:.35rem 1rem;font-size:.75rem;color:#64748b;border-top:1px solid #1e293b;'
        + 'background:#0f172a;min-height:28px;';
    card.appendChild(sbar);

    _modal.appendChild(card);
    document.body.appendChild(_modal);
    _ctx = _canvas.getContext('2d');

    // Eventos do modal
    _modal.addEventListener('click', function(e) { if (e.target === _modal) MyChart._close(); });
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && _modal.style.display !== 'none') MyChart._close();
        if ((e.key === 'l' || e.key === 'L') && _modal.style.display !== 'none') _setTool('line');
        if ((e.key === 'Escape' || e.key === 'c' || e.key === 'C') && _modal.style.display !== 'none') _setTool('cursor');
    });

    // Botões de período
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

    // MAs checkboxes
    ['mc-ma8','mc-ma20','mc-ma50'].forEach(function(id) {
        document.getElementById(id).onchange = function() { if (_state) _draw(); };
    });

    // Resize
    window.addEventListener('resize', function() { if (_state && _modal.style.display !== 'none') { _resize(); _draw(); } });

    // Eventos canvas
    _canvas.addEventListener('mousedown', _onMouseDown);
    _canvas.addEventListener('mousemove', _onMouseMove);
    _canvas.addEventListener('mouseup',   _onMouseUp);
    _canvas.addEventListener('mouseleave', function() {
        document.getElementById('mc-tooltip').style.display = 'none';
        document.getElementById('mc-crosshair-info').textContent = '';
        if (_state) { _state._crossX = null; _draw(); }
    });
}

function btnStyle(active) {
    return 'padding:.2rem .55rem;border-radius:4px;font-size:.78rem;cursor:pointer;border:none;'
        + 'background:' + (active ? '#3b82f6' : '#1e293b') + ';'
        + 'color:' + (active ? '#fff' : '#94a3b8') + ';'
        + 'font-weight:' + (active ? '600' : '400') + ';';
}
function toolBtn(active) {
    return 'padding:.2rem .55rem;border-radius:4px;font-size:.88rem;cursor:pointer;border:none;'
        + 'background:' + (active ? '#3b82f6' : '#1e293b') + ';color:' + (active ? '#fff' : '#94a3b8') + ';';
}

// ── Ferramenta cursor/linha ────────────────────────────────────────────────────
var _tool = 'cursor';
var _drawing = null;   // linha sendo desenhada

function _setTool(t) {
    _tool = t;
    document.getElementById('mc-tool-cursor').style.background = t === 'cursor' ? '#3b82f6' : '#1e293b';
    document.getElementById('mc-tool-cursor').style.color      = t === 'cursor' ? '#fff' : '#94a3b8';
    document.getElementById('mc-tool-line').style.background   = t === 'line'   ? '#3b82f6' : '#1e293b';
    document.getElementById('mc-tool-line').style.color        = t === 'line'   ? '#fff' : '#94a3b8';
    _canvas.style.cursor = t === 'line' ? 'crosshair' : 'default';
    _drawing = null;
}

// ── Coordenada canvas → data/price ────────────────────────────────────────────
function _px2data(cx, cy) {
    if (!_state || !_state._layout) return null;
    var l = _state._layout;
    var dpr = window.devicePixelRatio || 1;
    var rect = _canvas.getBoundingClientRect();
    // cx, cy são já em pixels canvas (sem dpr)
    var x = cx, y = cy;
    var i = Math.round((x - l.padL) / l.cw * (_state._vis.length - 1));
    i = Math.max(0, Math.min(_state._vis.length - 1, i));
    var price = l.priceMax - (y - l.padT) / l.ch * (l.priceMax - l.priceMin);
    var date = _state._vis[i] ? _state._vis[i].t : null;
    return { i: i, date: date, price: price };
}

function _clientToCanvas(e) {
    var rect = _canvas.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;
    return {
        x: (e.clientX - rect.left) * (_canvas.width / rect.width),
        y: (e.clientY - rect.top)  * (_canvas.height / rect.height)
    };
}

function _onMouseDown(e) {
    if (!_state) return;
    var pt = _clientToCanvas(e);
    var d  = _px2data(pt.x, pt.y);
    if (!d) return;

    if (_tool === 'line') {
        _drawing = { x1: d.date, y1: d.price, x2: d.date, y2: d.price };
    }
}

function _onMouseMove(e) {
    if (!_state || !_state._layout) return;
    var pt = _clientToCanvas(e);
    var d  = _px2data(pt.x, pt.y);

    // Atualiza estado (barato — sem rerender)
    _state._crossX = pt.x;
    _state._crossY = pt.y;
    _state._hoverD = d;
    _state._hoverE = e;

    if (_tool === 'line' && _drawing && d) {
        _drawing.x2 = d.date;
        _drawing.y2 = d.price;
    }

    // Throttle: máximo 1 rerender por frame de animação
    if (!_rafPending) {
        _rafPending = true;
        requestAnimationFrame(function() {
            _rafPending = false;
            if (!_state) return;
            _draw();
            var hd = _state._hoverD, he = _state._hoverE;
            if (hd && hd.date) {
                var c = _state._vis[hd.i];
                if (c) {
                    document.getElementById('mc-crosshair-info').textContent =
                        fmtDate(c.t) + '  A:' + fmtPrice(c.o) + '  H:' + fmtPrice(c.h)
                        + '  L:' + fmtPrice(c.l) + '  F:' + fmtPrice(c.c);
                }
            }
            if (hd && hd.date && _tool === 'cursor') {
                var c2 = _state._vis[hd.i];
                if (c2) {
                    var tip = document.getElementById('mc-tooltip');
                    tip.innerHTML = '<strong>' + fmtDate(c2.t) + '</strong>'
                        + '  A:<span style="color:#94a3b8">' + fmtPrice(c2.o) + '</span>'
                        + '  H:<span style="color:#4ade80">' + fmtPrice(c2.h) + '</span>'
                        + '  L:<span style="color:#f87171">' + fmtPrice(c2.l) + '</span>'
                        + '  F:<strong>' + fmtPrice(c2.c) + '</strong>'
                        + '  V:<span style="color:#94a3b8">' + (c2.v >= 1e6 ? (c2.v/1e6).toFixed(1)+'M' : c2.v >= 1e3 ? (c2.v/1e3).toFixed(0)+'k' : c2.v) + '</span>';
                    var rect = _canvas.getBoundingClientRect();
                    var tx = he.clientX - rect.left + 14;
                    var ty = he.clientY - rect.top  - 10;
                    if (tx + 340 > rect.width) tx = he.clientX - rect.left - 350;
                    tip.style.left = tx + 'px';
                    tip.style.top  = ty + 'px';
                    tip.style.display = 'block';
                }
            } else {
                var tip2 = document.getElementById('mc-tooltip');
                if (tip2) tip2.style.display = 'none';
            }
        });
    }
}

function _onMouseUp(e) {
    if (!_state || !_drawing) return;
    var pt = _clientToCanvas(e);
    var d  = _px2data(pt.x, pt.y);
    if (!d) { _drawing = null; return; }

    _drawing.x2 = d.date;
    _drawing.y2 = d.price;

    // Só salva se tiver tamanho mínimo
    var dx = Math.abs(pt.x - _data2px(_drawing.x1, _drawing.y1).x);
    var dy = Math.abs(pt.y - _data2px(_drawing.x2, _drawing.y2).y);
    if (dx < 5 && dy < 5) { _drawing = null; _draw(); return; }

    var line = { x1: _drawing.x1, y1: _drawing.y1, x2: _drawing.x2, y2: _drawing.y2,
                 color: '#3b82f6', width: 1.5 };
    _drawing = null;

    // Persiste
    fetch('/api/chart_lines/' + _state.ticker, {
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

function _data2px(date, price) {
    if (!_state || !_state._layout) return { x: 0, y: 0 };
    var l = _state._layout;
    var vis = _state._vis;
    var idx = -1;
    for (var i = 0; i < vis.length; i++) {
        if (vis[i].t <= date) idx = i;
        else if (idx >= 0) break;
    }
    if (idx < 0) idx = 0;
    var x = l.padL + (idx / (vis.length - 1)) * l.cw;
    var y = l.padT + (l.priceMax - price) / (l.priceMax - l.priceMin) * l.ch;
    return { x: x, y: y };
}

// ── Apagar linhas ──────────────────────────────────────────────────────────────
MyChart._delLines = function() {
    if (!_state) return;
    if (!confirm('Apagar todas as linhas de ' + _state.ticker + '?')) return;
    fetch('/api/chart_lines/' + _state.ticker, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body: JSON.stringify({})
    }).then(function() {
        _lines[_state.ticker] = [];
        _draw();
    });
};

// ── Abertura do gráfico ────────────────────────────────────────────────────────
MyChart.open = function(ticker, isIntl) {
    ticker = (ticker || '').toUpperCase().trim();
    // Determina ticker Yahoo Finance
    var yfticker = ticker;
    if (!isIntl && /^[A-Z]{4}[0-9]/.test(ticker) && ticker.indexOf('.') < 0) {
        yfticker = ticker + '.SA';
    }

    ensureModal();
    _modal.style.display = 'flex';
    document.getElementById('mc-title').textContent = '📈 ' + ticker;
    document.getElementById('mc-price').textContent = '';
    document.getElementById('mc-change').textContent = '';
    document.getElementById('mc-status').textContent = '⏳ Carregando dados…';

    _state = { ticker: ticker, yfticker: yfticker, period: '6mo',
               _vis: [], _layout: null, _crossX: null, _crossY: null };
    _setTool('cursor');
    _resize();

    // Carrega linhas salvas
    if (!_lines[ticker]) {
        fetch('/api/chart_lines/' + ticker)
            .then(function(r) { return r.json(); })
            .then(function(d) { _lines[ticker] = d; if (_state && _state.ticker === ticker) _draw(); });
    }

    // Cache cliente 2 min (camada 0 — zero round-trip)
    var now = Date.now();
    var cached = _cache[ticker];
    if (cached && (now - cached.ts) < 120000) {
        _state.allCandles = cached.candles;
        _applyPeriod(); _draw();
        return;
    }

    // Fetch incremental: se já temos candles, pede só os novos (?since=último_date)
    var url = '/api/chart_data/' + encodeURIComponent(ticker);
    var existingCandles = cached ? cached.candles : null;
    if (existingCandles && existingCandles.length) {
        url += '?since=' + existingCandles[existingCandles.length - 1].t;
    }

    fetch(url)
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.error) { document.getElementById('mc-status').textContent = '✗ ' + d.error; return; }
            var candles = d.candles;
            // Merge com candles existentes quando fetch incremental
            if (existingCandles && existingCandles.length && candles.length) {
                var newDates = {};
                candles.forEach(function(c) { newDates[c.t] = true; });
                var base = existingCandles.filter(function(c) { return !newDates[c.t]; });
                candles = base.concat(candles);
                candles.sort(function(a, b) { return a.t < b.t ? -1 : 1; });
            }
            _cache[ticker] = { ts: Date.now(), candles: candles };
            if (_state && _state.ticker === ticker) {
                _state.allCandles = candles;
                _applyPeriod(); _draw();
            }
        })
        .catch(function(e) { document.getElementById('mc-status').textContent = '✗ Erro: ' + e; });
};

MyChart._close = function() {
    if (_modal) _modal.style.display = 'none';
    _state = null;
};

// ── Filtro de período + pré-cálculo de MAs ────────────────────────────────────
function _applyPeriod() {
    if (!_state || !_state.allCandles) return;
    var all = _state.allCandles;
    var per = _state.period || '6mo';
    var days = { '1mo': 22, '3mo': 63, '6mo': 130 };
    var n = days[per] || 130;

    var warmup = 50;
    var start  = Math.max(0, all.length - n - warmup);
    var full   = all.slice(start);
    var closes = full.map(function(c) { return c.c; });

    var ma8f  = sma(closes, 8);
    var ma20f = sma(closes, 20);
    var ma50f = sma(closes, 50);

    var offset = full.length - Math.min(n, all.length);
    _state._vis   = full.slice(offset);
    _state._ma8   = ma8f.slice(offset);
    _state._ma20  = ma20f.slice(offset);
    _state._ma50  = ma50f.slice(offset);
}

// ── Resize canvas ──────────────────────────────────────────────────────────────
function _resize() {
    var dpr  = window.devicePixelRatio || 1;
    var wrap = document.getElementById('mc-canvas-wrap');
    if (!wrap) return;
    var W = wrap.clientWidth || 900;
    var H = Math.max(380, Math.round(W * 0.42));
    _canvas.width  = W * dpr;
    _canvas.height = H * dpr;
    _canvas.style.height = H + 'px';
    _ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    var vcvs = document.getElementById('mc-vol-canvas');
    if (vcvs) {
        var VH = Math.round(W * 0.08);
        vcvs.width  = W * dpr;
        vcvs.height = VH * dpr;
        vcvs.style.height = VH + 'px';
        vcvs.getContext('2d').setTransform(dpr, 0, 0, dpr, 0, 0);
    }
}

// ── Desenho principal ──────────────────────────────────────────────────────────
var PAD = { T: 32, R: 72, B: 28, L: 12 };

function _draw() {
    if (!_state || !_state._vis || !_state._vis.length) return;
    var vis = _state._vis;
    var dpr  = window.devicePixelRatio || 1;
    var W    = _canvas.width  / dpr;
    var H    = _canvas.height / dpr;
    var ctx  = _ctx;

    ctx.clearRect(0, 0, W, H);

    // Layout
    var padL = PAD.L, padR = PAD.R, padT = PAD.T, padB = PAD.B;
    var cW = W - padL - padR;
    var cH = H - padT - padB;

    // Preço range
    var priceMin = Infinity, priceMax = -Infinity;
    for (var i = 0; i < vis.length; i++) {
        if (vis[i].l < priceMin) priceMin = vis[i].l;
        if (vis[i].h > priceMax) priceMax = vis[i].h;
    }
    var pad5 = (priceMax - priceMin) * 0.05 || priceMax * 0.01;
    priceMin -= pad5; priceMax += pad5;

    _state._layout = { padL: padL, padR: padR, padT: padT, padB: padB,
                       cW: cW, cH: cH, priceMin: priceMin, priceMax: priceMax };

    function xPx(i) { return padL + (i / (vis.length - 1 || 1)) * cW; }
    function yPx(p) { return padT + (1 - (p - priceMin) / (priceMax - priceMin)) * cH; }

    // Fundo
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, W, H);

    // Grade horizontal
    ctx.strokeStyle = 'rgba(51,65,85,.5)';
    ctx.lineWidth = 1;
    var nLines = 6;
    for (var i = 0; i <= nLines; i++) {
        var yg = padT + i * cH / nLines;
        ctx.beginPath(); ctx.moveTo(padL, yg); ctx.lineTo(W - padR, yg); ctx.stroke();
        var pLabel = priceMax - i * (priceMax - priceMin) / nLines;
        ctx.fillStyle = '#64748b';
        ctx.font = '10px Inter,sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText(fmtPrice(pLabel), W - padR + 4, yg + 4);
    }

    // Grade vertical + labels data
    var dateStep = Math.max(1, Math.floor(vis.length / 8));
    ctx.fillStyle = '#64748b'; ctx.font = '10px Inter,sans-serif'; ctx.textAlign = 'center';
    for (var i = 0; i < vis.length; i += dateStep) {
        var xg = xPx(i);
        ctx.strokeStyle = 'rgba(51,65,85,.35)'; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(xg, padT); ctx.lineTo(xg, H - padB); ctx.stroke();
        ctx.fillText(fmtDate(vis[i].t), xg, H - padB + 14);
    }

    // MAs pré-calculadas em _applyPeriod — zero recomputo por frame
    var showMA8   = document.getElementById('mc-ma8')   && document.getElementById('mc-ma8').checked;
    var showMA20  = document.getElementById('mc-ma20')  && document.getElementById('mc-ma20').checked;
    var showMA50 = document.getElementById('mc-ma50') && document.getElementById('mc-ma50').checked;

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

    if (showMA50) drawMA(_state._ma50, '#f87171', 1.2);
    if (showMA20)  drawMA(_state._ma20,  '#60a5fa', 1.2);
    if (showMA8)   drawMA(_state._ma8,   '#fbbf24', 1.0);

    // Candles
    var candleW = Math.max(1, Math.min(14, cW / vis.length * 0.7));
    for (var i = 0; i < vis.length; i++) {
        var c = vis[i];
        var bull = c.c >= c.o;
        var col  = bull ? '#26a69a' : '#ef5350';
        var xc   = xPx(i);
        var yH = yPx(c.h), yL = yPx(c.l);
        var yO = yPx(c.o), yC = yPx(c.c);
        // Pavio
        ctx.strokeStyle = col; ctx.lineWidth = 1; ctx.setLineDash([]);
        ctx.beginPath(); ctx.moveTo(xc, yH); ctx.lineTo(xc, yL); ctx.stroke();
        // Corpo
        var bodyTop = Math.min(yO, yC);
        var bodyH   = Math.max(1, Math.abs(yC - yO));
        ctx.fillStyle = col;
        ctx.fillRect(xc - candleW / 2, bodyTop, candleW, bodyH);
    }

    // Linhas de tendência salvas
    var savedLines = _lines[_state.ticker] || [];
    savedLines.forEach(function(ln) {
        var p1 = _data2px(ln.x1, ln.y1);
        var p2 = _data2px(ln.x2, ln.y2);
        ctx.strokeStyle = ln.color || '#3b82f6';
        ctx.lineWidth   = ln.width || 1.5;
        ctx.setLineDash([]);
        ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.stroke();
        // Pequeno círculo nas extremidades
        ctx.fillStyle = ln.color || '#3b82f6';
        ctx.beginPath(); ctx.arc(p1.x, p1.y, 3, 0, 2 * Math.PI); ctx.fill();
        ctx.beginPath(); ctx.arc(p2.x, p2.y, 3, 0, 2 * Math.PI); ctx.fill();
    });

    // Linha sendo desenhada agora
    if (_drawing) {
        var p1 = _data2px(_drawing.x1, _drawing.y1);
        var p2 = _data2px(_drawing.x2, _drawing.y2);
        ctx.strokeStyle = '#fbbf24'; ctx.lineWidth = 1.5; ctx.setLineDash([4, 3]);
        ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.stroke();
        ctx.setLineDash([]);
    }

    // Crosshair
    if (_state._crossX != null) {
        ctx.strokeStyle = 'rgba(148,163,184,.45)'; ctx.lineWidth = 1; ctx.setLineDash([3, 3]);
        ctx.beginPath(); ctx.moveTo(_state._crossX, padT); ctx.lineTo(_state._crossX, H - padB); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(padL, _state._crossY); ctx.lineTo(W - padR, _state._crossY); ctx.stroke();
        ctx.setLineDash([]);
        // Label preço no eixo Y
        var pCross = priceMax - (_state._crossY - padT) / cH * (priceMax - priceMin);
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(W - padR + 1, _state._crossY - 9, padR - 2, 18);
        ctx.fillStyle = '#e2e8f0'; ctx.font = 'bold 10px Inter,sans-serif'; ctx.textAlign = 'left';
        ctx.fillText(fmtPrice(pCross), W - padR + 4, _state._crossY + 4);
    }

    // Preço último (linha horizontal)
    var lastClose = vis[vis.length - 1].c;
    var yLast = yPx(lastClose);
    var prevClose = vis.length > 1 ? vis[vis.length - 2].c : lastClose;
    var lastColor = lastClose >= prevClose ? '#26a69a' : '#ef5350';
    ctx.strokeStyle = lastColor; ctx.lineWidth = 1; ctx.setLineDash([4, 3]);
    ctx.beginPath(); ctx.moveTo(padL, yLast); ctx.lineTo(W - padR, yLast); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = lastColor;
    ctx.fillRect(W - padR + 1, yLast - 9, padR - 2, 18);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 10px Inter,sans-serif'; ctx.textAlign = 'left';
    ctx.fillText(fmtPrice(lastClose), W - padR + 4, yLast + 4);

    // Header: preço + variação
    var chgPct = ((lastClose - prevClose) / prevClose * 100);
    document.getElementById('mc-price').textContent = 'R$ ' + fmtPrice(lastClose);
    var chgEl = document.getElementById('mc-change');
    chgEl.textContent = (chgPct >= 0 ? '+' : '') + chgPct.toFixed(2).replace('.', ',') + '%';
    chgEl.style.color = chgPct >= 0 ? '#26a69a' : '#ef5350';

    // Status bar
    document.getElementById('mc-status').textContent =
        vis.length + ' candles  |  ' + fmtDate(vis[0].t) + ' – ' + fmtDate(vis[vis.length - 1].t)
        + '  |  Teclas: L=linha  C/Esc=cursor';

    // Volume
    _drawVolume(vis);
}

function _drawVolume(vis) {
    var vcvs = document.getElementById('mc-vol-canvas');
    if (!vcvs) return;
    var dpr = window.devicePixelRatio || 1;
    var W   = vcvs.width  / dpr;
    var H   = vcvs.height / dpr;
    var ctx2 = vcvs.getContext('2d');
    ctx2.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx2.clearRect(0, 0, W, H);
    ctx2.fillStyle = '#0f172a'; ctx2.fillRect(0, 0, W, H);

    var cW = W - PAD.L - PAD.R;
    var maxV = Math.max.apply(null, vis.map(function(c) { return c.v; })) || 1;

    function xPx(i) { return PAD.L + (i / (vis.length - 1 || 1)) * cW; }
    var barW = Math.max(1, cW / vis.length * 0.7);

    for (var i = 0; i < vis.length; i++) {
        var c = vis[i];
        var bH = (c.v / maxV) * (H - 4);
        ctx2.fillStyle = c.c >= c.o ? 'rgba(38,166,154,.6)' : 'rgba(239,83,80,.6)';
        ctx2.fillRect(xPx(i) - barW / 2, H - bH, barW, bH);
    }
}

// ── API pública ────────────────────────────────────────────────────────────────
global.MyChart = global.MyChart || {};
global.MyChart.open   = MyChart.open;
global.MyChart._close = MyChart._close;
global.MyChart._delLines = MyChart._delLines;

// Compatibilidade: buildTVWidget e openTVChart agora chamam MyChart.open
global.buildTVWidget = function(containerId, symbol, theme, height) {
    // Remove prefixo BMFBOVESPA: se vier
    var ticker = symbol.replace(/^BMFBOVESPA:/, '').replace(/\.SA$/, '');
    var isIntl = !/^[A-Z]{4}[0-9]/.test(ticker);
    MyChart.open(ticker, isIntl);
};

})(window);
