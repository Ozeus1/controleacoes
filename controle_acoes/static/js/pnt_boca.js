/**
 * PntBoca — modal "enviar para o Pnt": busca a boca (bid/ask) das pernas, calcula a boca de execução imediata,
 * sugere um valor que NÃO cruza o book (o Pnt só aceita ofertas melhores que o book; uma oferta que executaria
 * na hora é recusada) e copia a linha no formato do Pnt:
 *     TICKERS(TAB) C/V(TAB) QUANTIDADES(TAB) BOCA        — boca: + paga (débito) · − recebe (crédito), por unidade da 1ª perna
 *
 * Uso:  PntBoca.abrir({
 *   titulo, tituloOperacao, tituloInfo, infoHtml(ctx)|string,
 *   pernas: [{ticker, acao:'BUY'|'SELL' (ordem a executar), origem:'BUY'|'SELL'|null, qty, tipo, strike, exp, ref, cols:[...]}],
 *   colunasPerna: [{titulo, tip}],          // colunas extras da tabela (valores em pernas[i].cols)
 *   rotuloRef: 'Pelo atual',                // sugestão calculada com os preços "ref" das pernas
 *   resumoColunas: [{titulo, html:function(c, ctx)}],   // c = boca (coeficiente do Pnt) ou null
 *   notaResumo: 'texto'
 * })
 * ctx = {qty1, cash(c), nf, brl, cd, sgn, pct}   cash(c) = fluxo de caixa total da ordem na boca c (+ recebe)
 */
(function (global) {
    'use strict';
    var TAB = String.fromCharCode(9);
    var S = { o: null, legs: [], books: null, meta: null, B: null };

    function $(id) { return document.getElementById(id); }
    function nf(v, d) { d = d == null ? 2 : d; return Number(v).toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d }); }
    function brl(v) { return (v < 0 ? '−' : '') + 'R$ ' + nf(Math.abs(v)); }
    function cd(v) { return brl(Math.abs(v)) + (v >= 0 ? ' (crédito)' : ' (débito)'); }          // v = fluxo de caixa (+ recebe)
    function sgn(v) { return (v > 0 ? '+' : v < 0 ? '−' : '') + 'R$ ' + nf(Math.abs(v)); }
    function pct(v) { return (v >= 0 ? '+' : '−') + nf(Math.abs(v)) + '%'; }
    function coefTxt(c) { return c.toFixed(2).replace('.', ','); }
    function esc(t) { return String(t == null ? '' : t).replace(/[&<>"]/g, function (m) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m]; }); }
    function pos(v) { v = parseFloat(v); return v > 0 ? v : null; }

    function qty1() { return S.legs[0] ? S.legs[0].qty : 1; }
    function cashDe(precos) { return S.legs.reduce(function (a, l, i) { return a + (l.acao === 'SELL' ? 1 : -1) * l.qty * precos[i]; }, 0); }
    function coefDe(precos) { return precos.some(function (p) { return p == null; }) ? null : -cashDe(precos) / qty1(); }   // Pnt: + paga · − recebe
    function bk(l) { return (S.books && S.books[l.ticker]) || {}; }
    function precosBoca() { return S.legs.map(function (l) { var b = bk(l); return l.acao === 'BUY' ? pos(b.ask) : pos(b.bid); }); }
    function precosMid() { return S.legs.map(function (l) { var b = bk(l); return (pos(b.bid) && pos(b.ask)) ? (b.bid + b.ask) / 2 : null; }); }
    function precosRef() { return S.legs.map(function (l) { return l.ref > 0 ? l.ref : null; }); }
    function maiorAbaixo(B) { return (Math.ceil(B * 100 - 1e-9) - 1) / 100; }          // maior múltiplo de R$ 0,01 estritamente menor que B
    function coefDigitado() { var el = $('pb-coef'); var v = parseFloat(String(el ? el.value : '').replace(',', '.')); return isNaN(v) ? null : v; }
    function ctx() { return { qty1: qty1(), cash: function (c) { return -c * qty1(); }, nf: nf, brl: brl, cd: cd, sgn: sgn, pct: pct }; }
    function linhaPnt(c) {
        return S.legs.map(function (l) { return l.ticker; }).concat(S.legs.map(function (l) { return l.acao === 'BUY' ? 'C' : 'V'; }))
            .concat(S.legs.map(function (l) { return l.qty; })).concat([coefTxt(c)]).join(TAB);
    }

    function montaModal() {
        if ($('pb-modal')) return;
        var d = document.createElement('div');
        d.id = 'pb-modal';
        d.style.cssText = 'display:none;position:fixed;inset:0;z-index:19200;background:rgba(0,0,0,.78);align-items:center;justify-content:center;padding:1rem;';
        d.innerHTML =
            '<div style="background:var(--card-bg,#1e293b);border-radius:10px;width:min(98vw,980px);max-height:94vh;display:flex;flex-direction:column;border:1px solid var(--border-color);">' +
            '<div style="display:flex;justify-content:space-between;align-items:center;padding:.8rem 1.1rem;border-bottom:1px solid var(--border-color);">' +
            '<h3 id="pb-titulo" style="margin:0;font-size:1.02rem;"></h3>' +
            '<button type="button" id="pb-x" style="background:none;border:none;font-size:1.4rem;color:var(--text-secondary);cursor:pointer;line-height:1;">&times;</button></div>' +
            '<div id="pb-body" style="flex:1;overflow-y:auto;padding:.9rem 1.1rem;font-size:.86rem;"></div>' +
            '<div style="display:flex;justify-content:flex-end;gap:.5rem;padding:.7rem 1.1rem;border-top:1px solid var(--border-color);flex-wrap:wrap;">' +
            '<button type="button" class="btn btn-secondary btn-sm" id="pb-fechar">Fechar</button>' +
            '<button type="button" class="btn btn-secondary btn-sm" id="pb-atualiza" title="Busca de novo o book (bid/ask) das pernas">🔄 Atualizar book</button>' +
            '<button type="button" class="btn btn-sm" id="pb-copiar" style="background:#ef4444;border:1px solid #ef4444;color:#fff;font-weight:700;">📋 Copiar para o Pnt</button>' +
            '</div></div>';
        document.body.appendChild(d);
        $('pb-x').addEventListener('click', fechar);
        $('pb-fechar').addEventListener('click', fechar);
        $('pb-atualiza').addEventListener('click', carrega);
        $('pb-copiar').addEventListener('click', copia);
        d.addEventListener('click', function (e) { if (e.target === d) fechar(); });
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape') fechar(); });
    }
    function fechar() { var m = $('pb-modal'); if (m) m.style.display = 'none'; }

    function render() {
        var o = S.o, legs = S.legs;
        var B = coefDe(precosBoca()), M = coefDe(precosMid()), R = coefDe(precosRef());
        var sug = B != null ? maiorAbaixo(B) : null;
        if (M != null && B != null && M >= B) M = null;                  // ponto médio que já cruzaria: não sugere
        var x = ctx(), h = '';
        // 1) operação a executar
        h += '<div style="margin-bottom:.35rem;font-weight:700;">' + esc(o.tituloOperacao || '1) Operação a executar') + '</div>';
        h += '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:.82rem;"><thead><tr style="color:var(--text-secondary);text-align:right;">' +
             '<th style="text-align:left;padding:.25rem .4rem;">Ordem</th><th>Qtd</th><th style="text-align:left;">Ticker</th><th>Tipo</th><th>Strike</th><th>Venc.</th>';
        (o.colunasPerna || []).forEach(function (c) { h += '<th title="' + esc(c.tip || '') + '">' + esc(c.titulo) + '</th>'; });
        h += '<th>Bid</th><th>Ask</th><th title="Preço de execução imediata: compra no ask, venda no bid">Boca (imediata)</th></tr></thead><tbody>';
        legs.forEach(function (l) {
            var b = bk(l), imed = l.acao === 'BUY' ? pos(b.ask) : pos(b.bid);
            var venc = l.exp ? String(l.exp).slice(8, 10) + '/' + String(l.exp).slice(5, 7) + '/' + String(l.exp).slice(0, 4) : '—';
            h += '<tr style="border-top:1px solid var(--border-color);text-align:right;">' +
                 '<td style="text-align:left;padding:.3rem .4rem;"><span style="display:inline-block;min-width:1.5rem;text-align:center;padding:.1rem .45rem;border-radius:4px;font-weight:700;background:' +
                 (l.acao === 'SELL' ? 'rgba(239,68,68,.18);color:#f87171' : 'rgba(16,185,129,.18);color:#34d399') + ';">' + (l.acao === 'SELL' ? 'V' : 'C') + '</span>' +
                 (l.origem ? ' <span style="color:var(--text-secondary);font-size:.72rem;">(era ' + (l.origem === 'SELL' ? 'V' : 'C') + ')</span>' : '') + '</td>' +
                 '<td>' + l.qty + '</td><td style="text-align:left;"><span class="ticker-badge">' + esc(l.ticker) + '</span></td><td>' + esc(l.tipo || '') + '</td><td>' + (l.strike ? nf(l.strike) : '—') + '</td><td>' + venc + '</td>';
            (l.cols || []).forEach(function (v) { h += '<td>' + (v != null && v > 0 ? nf(v) : '—') + '</td>'; });
            h += '<td>' + (pos(b.bid) ? nf(b.bid) : '—') + '</td><td>' + (pos(b.ask) ? nf(b.ask) : '—') + '</td>' +
                 '<td style="font-weight:700;">' + (imed ? nf(imed) : '<span style="color:#fbbf24;">sem book</span>') + '</td></tr>';
        });
        h += '</tbody></table></div>';
        var fontes = {};
        legs.forEach(function (l) {
            var b = bk(l); if (!b.fonte) return;
            fontes[b.fonte + (b.atualizado ? ' ' + b.atualizado + (b.idade_min != null ? ' (há ' + (b.idade_min < 60 ? b.idade_min + ' min' : Math.floor(b.idade_min / 60) + ' h') + ')' : '') : ' ao vivo')] = 1;
        });
        var ft = Object.keys(fontes).join(' · ');
        h += '<div style="font-size:.74rem;color:var(--text-secondary);margin:.3rem 0 .8rem;">Book: ' + (ft ? esc(ft) : '<span style="color:#fbbf24;">indisponível</span>') +
             (S.meta && S.meta.market_open === false ? ' · <span style="color:#fbbf24;">pregão fechado — bid/ask podem estar vazios ou antigos</span>' : '') +
             (legs.some(function (l) { return pos(bk(l).ask) == null || pos(bk(l).bid) == null; }) ? ' · <span style="color:#fbbf24;">há perna sem bid/ask: a boca completa não pode ser calculada</span>' : '') + '</div>';

        // 2) informações da operação (montagem / simulação)
        if (o.infoHtml) {
            h += '<div style="margin-bottom:.35rem;font-weight:700;">' + esc(o.tituloInfo || '2) Operação') + '</div>';
            h += '<div style="margin-bottom:.8rem;">' + (typeof o.infoHtml === 'function' ? o.infoHtml(x) : o.infoHtml) + '</div>';
        }

        // 3) boca e preço a enviar
        h += '<div style="margin-bottom:.35rem;font-weight:700;">3) Boca para enviar ao Pnt <span style="font-weight:400;color:var(--text-secondary);">(+ paga · − recebe, por unidade da 1ª perna: ' + qty1() + ')</span></div>';
        h += '<div style="display:flex;gap:.9rem;flex-wrap:wrap;align-items:flex-end;margin-bottom:.5rem;">';
        h += '<div><div style="font-size:.74rem;color:var(--text-secondary);">Boca atual (execução imediata)</div><div style="font-size:1.05rem;font-weight:700;">' +
             (B != null ? coefTxt(B) + ' <span style="font-size:.74rem;font-weight:400;">' + (B > 0 ? '(pagaria ' + brl(B * qty1()) + ' agora)' : B < 0 ? '(receberia ' + brl(-B * qty1()) + ' agora)' : '') + '</span>' : '—') + '</div></div>';
        h += '<div><div style="font-size:.74rem;color:var(--text-secondary);">Boca a enviar</div><input id="pb-coef" type="text" inputmode="decimal" style="width:110px;text-align:right;font-size:1rem;font-weight:700;' +
             'background:var(--input-bg,#0f172a);color:var(--text-primary);border:1px solid var(--border-color);border-radius:6px;padding:.3rem .5rem;" value="' + (sug != null ? coefTxt(sug) : (R != null ? coefTxt(R) : '')) + '"></div>';
        h += '<div style="display:flex;gap:.35rem;flex-wrap:wrap;">';
        if (sug != null) h += '<button type="button" class="btn btn-secondary btn-sm" data-sug="' + coefTxt(sug) + '" title="Maior valor que ainda NÃO cruza o book (1 tick melhor que a boca)">Passivo: ' + coefTxt(sug) + '</button>';
        if (M != null) h += '<button type="button" class="btn btn-secondary btn-sm" data-sug="' + coefTxt(Math.round(M * 100) / 100) + '" title="Ponto médio entre bid e ask de cada perna">Médio: ' + coefTxt(Math.round(M * 100) / 100) + '</button>';
        if (R != null) h += '<button type="button" class="btn btn-secondary btn-sm" data-sug="' + coefTxt(R) + '" title="Calculado com os preços da tela (pode cruzar o book)">' + esc(o.rotuloRef || 'Pelo preço da tela') + ': ' + coefTxt(R) + '</button>';
        h += '</div></div><div id="pb-valida" style="margin-bottom:.8rem;"></div>';

        // 4) resumo financeiro
        var cols = o.resumoColunas || [];
        h += '<div style="margin-bottom:.35rem;font-weight:700;">4) Resumo financeiro</div>';
        h += '<div style="overflow-x:auto;"><table id="pb-resumo" style="width:100%;border-collapse:collapse;font-size:.84rem;"><thead><tr style="color:var(--text-secondary);"><th style="text-align:left;padding:.25rem .4rem;"></th>';
        cols.forEach(function (c) { h += '<th style="text-align:right;padding:.25rem .4rem;white-space:normal;line-height:1.15;font-size:.74rem;">' + esc(c.titulo) + '</th>'; });
        h += '</tr></thead><tbody><tr id="pb-boca-row" style="border-top:1px solid var(--border-color);"><td style="padding:.3rem .4rem;">Na boca agora <span style="color:var(--text-secondary);font-size:.72rem;">(execução imediata)</span></td>';
        cols.forEach(function (c) { h += '<td style="text-align:right;padding:.3rem .4rem;">' + (B == null ? '<span style="color:var(--text-secondary);">—</span>' : c.html(B, x)) + '</td>'; });
        h += '</tr><tr id="pb-env" style="border-top:1px solid var(--border-color);"><td style="padding:.3rem .4rem;"><strong>No preço que vou enviar</strong></td>';
        cols.forEach(function (c, i) { h += '<td style="text-align:right;padding:.3rem .4rem;" data-pbc="' + i + '"></td>'; });
        h += '</tr></tbody></table></div>';
        if (o.notaResumo) h += '<div style="font-size:.72rem;color:var(--text-secondary);margin-top:.35rem;">' + esc(o.notaResumo) + ' O fluxo da ordem é a boca × a quantidade da 1ª perna (' + qty1() + ').</div>';

        // 5) linha do Pnt
        h += '<div style="margin:.8rem 0 .35rem;font-weight:700;">5) Linha para o Pnt</div><pre id="pb-linha" style="margin:0;background:var(--bg-color,#0f172a);border:1px solid var(--border-color);border-radius:6px;padding:.55rem .7rem;overflow-x:auto;font-size:.82rem;"></pre>';
        $('pb-body').innerHTML = h;
        $('pb-body').querySelectorAll('[data-sug]').forEach(function (b) { b.addEventListener('click', function () { $('pb-coef').value = b.dataset.sug; atualiza(); }); });
        $('pb-coef').addEventListener('input', atualiza);
        S.B = B;
        atualiza();
    }

    function atualiza() {
        var c = coefDigitado(), v = $('pb-valida'), x = ctx(), cols = S.o.resumoColunas || [];
        cols.forEach(function (col, i) { var td = document.querySelector('#pb-env [data-pbc="' + i + '"]'); if (td) td.innerHTML = c == null ? '—' : col.html(c, x); });
        if (c == null) { v.innerHTML = '<span style="color:#fbbf24;">Informe a boca a enviar.</span>'; $('pb-linha').textContent = ''; return; }
        var B = S.B;
        if (B == null) v.innerHTML = '<span style="color:#fbbf24;">⚠ Sem bid/ask completo: não consigo conferir se esse valor cruza o book. Confira no Pnt.</span>';
        else if (c >= B - 1e-9) v.innerHTML = '<span style="color:#f87171;font-weight:700;">⛔ Cruza o book: executaria na hora (compra/venda imediata) e o Pnt não aceita. Use no máximo ' + coefTxt(maiorAbaixo(B)) + '.</span>';
        else v.innerHTML = '<span style="color:#34d399;font-weight:700;">✓ Não cruza o book: a ordem fica no livro. ' + coefTxt(B - c) + ' abaixo da boca atual (' + coefTxt(B) + ').</span>';
        $('pb-linha').textContent = linhaPnt(c).split(TAB).join('    ');
    }

    function carrega() {
        var tk = S.legs.map(function (l) { return l.ticker; });
        $('pb-body').innerHTML = '<div style="padding:1rem;color:var(--text-secondary);">⏳ buscando o book das pernas…</div>';
        fetch('/api/payoff-reverter/books', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tickers: tk }), credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(function (j) { S.books = j.books || {}; S.meta = j; render(); })
            .catch(function () { S.books = {}; S.meta = {}; render(); });
    }

    function copia() {
        var c = coefDigitado(); if (c == null) { alert('Informe a boca a enviar.'); return; }
        if (S.B != null && c >= S.B - 1e-9 && !confirm('Esse valor cruza o book (execução imediata) e o Pnt não aceita.\n\nCopiar mesmo assim?')) return;
        var linha = linhaPnt(c), btn = $('pb-copiar'), orig = btn.textContent;
        function ok() { btn.textContent = '✓ Copiado!'; setTimeout(function () { btn.textContent = orig; }, 1500); }
        function fail() { prompt('Copie a ordem (Pnt):', linha); }
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(linha).then(ok, fail); else fail();
    }

    function abrir(o) {
        S.o = o; S.legs = (o.pernas || []).filter(function (l) { return l.ticker && l.qty > 0; }); S.books = null; S.meta = null; S.B = null;
        if (!S.legs.length) { alert('Preencha ao menos uma perna de opção com ticker e quantidade.'); return; }
        montaModal();
        if (document.fullscreenElement && document.exitFullscreen) document.exitFullscreen();
        $('pb-titulo').textContent = o.titulo || 'Enviar para o Pnt';
        $('pb-modal').style.display = 'flex';
        carrega();
    }

    global.PntBoca = { abrir: abrir, fechar: fechar };
})(window);
