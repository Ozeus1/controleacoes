/* Modal "Ver Gráfico": candles de 5min do dia seguinte ao cálculo dos
 * Walls, com os principais walls e o Flip desenhados como linhas
 * horizontais — leitura visual de onde o gama concentrado bateu contra o
 * preço real no pregão em que o indicador passou a valer.
 *
 * Candlestick desenhado em canvas puro (sem lib externa), no mesmo espírito
 * do MyChart já usado no projeto. Duas instâncias independentes: o modal
 * normal (fixo, sem interação) e um modal "expandido" (zoom por roda do
 * mouse, pan por arrastar, tooltip de hover) — a mesma função de desenho
 * atende as duas, parametrizada por um objeto de view (janela de zoom/pan).
 */
(function (global) {
  'use strict';

  var _modal = null, _modalGrande = null;
  var _ultimoEstado = null;   // {candles, linhas, spot, titulo, sub} — p/ reabrir expandido

  function ensureModal() {
    if (_modal) return;
    _modal = document.createElement('div');
    _modal.id = 'wcm-modal';
    _modal.style.cssText = 'display:none;position:fixed;inset:0;z-index:9999;' +
      'background:rgba(0,0,0,.6);align-items:center;justify-content:center;padding:1rem;';
    _modal.innerHTML =
      '<div style="background:var(--card-bg,#0f172a);border:1px solid var(--border-color,#334155);' +
      'border-radius:10px;max-width:960px;width:100%;max-height:92vh;overflow:auto;padding:1rem 1.2rem;">' +
      '  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.6rem;">' +
      '    <h3 id="wcm-titulo" style="margin:0;font-size:1.05rem;color:var(--text-primary,#f1f5f9);"></h3>' +
      '    <div style="display:flex;gap:.5rem;align-items:center;">' +
      '      <button type="button" id="wcm-expandir" class="btn btn-secondary btn-sm" title="Abrir em janela maior, com zoom e pan">⤢ Expandir</button>' +
      '      <button type="button" id="wcm-fechar" style="background:none;border:none;font-size:1.3rem;' +
      '              color:var(--text-secondary,#94a3b8);cursor:pointer;line-height:1;">✕</button>' +
      '    </div>' +
      '  </div>' +
      '  <p id="wcm-sub" style="margin:0 0 .6rem;font-size:.82rem;color:var(--text-secondary,#94a3b8);"></p>' +
      '  <div id="wcm-legenda" style="display:flex;gap:1rem;flex-wrap:wrap;font-size:.78rem;' +
      '       color:var(--text-secondary,#94a3b8);margin-bottom:.5rem;"></div>' +
      '  <div id="wcm-status" style="text-align:center;padding:2rem;color:var(--text-secondary,#94a3b8);"></div>' +
      '  <div id="wcm-canvas-wrap" style="position:relative;height:460px;display:none;">' +
      '    <canvas id="wcm-canvas" style="width:100%;height:100%;display:block;"></canvas>' +
      '    <div id="wcm-tooltip" style="position:absolute;display:none;pointer-events:none;' +
      '         background:rgba(15,23,42,.95);border:1px solid #334155;border-radius:5px;' +
      '         padding:.3rem .5rem;font-size:.75rem;color:#f1f5f9;white-space:nowrap;z-index:2;"></div>' +
      '  </div>' +
      '</div>';
    document.body.appendChild(_modal);
    document.getElementById('wcm-fechar').onclick = fechar;
    document.getElementById('wcm-expandir').onclick = abrirExpandido;
    _modal.addEventListener('click', function (e) { if (e.target === _modal) fechar(); });
  }

  function ensureModalGrande() {
    if (_modalGrande) return;
    _modalGrande = document.createElement('div');
    _modalGrande.id = 'wcmg-modal';
    _modalGrande.style.cssText = 'display:none;position:fixed;inset:0;z-index:10000;' +
      'background:rgba(0,0,0,.75);align-items:center;justify-content:center;padding:.6rem;';
    _modalGrande.innerHTML =
      '<div style="background:var(--card-bg,#0f172a);border:1px solid var(--border-color,#334155);' +
      'border-radius:10px;width:100%;height:100%;max-width:1600px;padding:.8rem 1rem;' +
      'display:flex;flex-direction:column;">' +
      '  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.4rem;flex-shrink:0;">' +
      '    <h3 id="wcmg-titulo" style="margin:0;font-size:1.1rem;color:var(--text-primary,#f1f5f9);"></h3>' +
      '    <div style="display:flex;gap:.6rem;align-items:center;">' +
      '      <button type="button" id="wcmg-reset" class="btn btn-secondary btn-sm">↺ Resetar zoom</button>' +
      '      <button type="button" id="wcmg-fechar" style="background:none;border:none;font-size:1.5rem;' +
      '              color:var(--text-secondary,#94a3b8);cursor:pointer;line-height:1;">✕</button>' +
      '    </div>' +
      '  </div>' +
      '  <p id="wcmg-sub" style="margin:0 0 .4rem;font-size:.85rem;color:var(--text-secondary,#94a3b8);flex-shrink:0;"></p>' +
      '  <div id="wcmg-legenda" style="display:flex;gap:1.1rem;flex-wrap:wrap;font-size:.8rem;' +
      '       color:var(--text-secondary,#94a3b8);margin-bottom:.5rem;flex-shrink:0;"></div>' +
      '  <p style="margin:0 0 .5rem;font-size:.74rem;color:var(--text-secondary,#94a3b8);flex-shrink:0;">' +
      '    Roda do mouse para zoom · roda sobre o eixo de preço (esquerda) para abrir/fechar a escala vertical · arraste para mover · duplo clique para resetar' +
      '  </p>' +
      '  <div id="wcmg-canvas-wrap" style="position:relative;flex:1;min-height:0;">' +
      '    <canvas id="wcmg-canvas" style="width:100%;height:100%;display:block;cursor:grab;"></canvas>' +
      '    <div id="wcmg-tooltip" style="position:absolute;display:none;pointer-events:none;' +
      '         background:rgba(15,23,42,.95);border:1px solid #334155;border-radius:5px;' +
      '         padding:.35rem .6rem;font-size:.8rem;color:#f1f5f9;white-space:nowrap;z-index:2;"></div>' +
      '  </div>' +
      '</div>';
    document.body.appendChild(_modalGrande);
    document.getElementById('wcmg-fechar').onclick = function () { _modalGrande.style.display = 'none'; };
    _modalGrande.addEventListener('click', function (e) { if (e.target === _modalGrande) _modalGrande.style.display = 'none'; });
  }

  function fechar() {
    if (_modal) _modal.style.display = 'none';
  }

  var CORES_WALL = { clWall: '#a3e635', clMidWall: '#94a3b8', clMidWallFibo: '#475569',
                     clFlip: '#facc15', clMaxGamma: '#34d399', clMinGamma: '#f87171' };
  var NOMES_WALL = { clWall: 'Wall', clMidWall: 'MidWall', clMidWallFibo: 'Fibo 11,8%',
                     clFlip: 'Flip', clMaxGamma: 'Gama máximo', clMinGamma: 'Gama mínimo' };

  function fmtEixo(v) {
    return v >= 1000 ? Math.round(v).toLocaleString('pt-BR') : Number(v).toFixed(2).replace('.', ',');
  }

  /**
   * Calcula a janela de valores (vmin/vmax) e monta as funções de projeção
   * pixel<->valor para um estado de view (zoom/pan). `view` é opcional —
   * sem ele, usa o range "ajustado" (candles + folga), igual ao modal
   * simples; com ele, aplica o fator de zoom e o deslocamento de pan.
   */
  function montaEscala(candles, spot, view, W, H, padL, padR, padT, padB) {
    var plotW = W - padL - padR, plotH = H - padT - padB;
    var valsCandle = [];
    candles.forEach(function (c) { valsCandle.push(c.h, c.l); });
    if (spot) valsCandle.push(spot);
    var vminBase = Math.min.apply(null, valsCandle), vmaxBase = Math.max.apply(null, valsCandle);
    var folga = (vmaxBase - vminBase) * 0.10 || Math.abs(vminBase) * 0.01 || 1;
    vminBase -= folga; vmaxBase += folga;

    var zoomX = (view && (view.zoomX || view.zoom)) || 1;
    var zoomY = (view && view.zoomY) || 1;
    var panX = (view && view.panX) || 0;   // em "candles" deslocados
    var panY = (view && view.panY) || 0;   // em unidades de valor

    var nVis = candles.length / zoomX;
    var centroI = candles.length / 2 - panX;
    var iMin = centroI - nVis / 2, iMax = centroI + nVis / 2;

    var vmin = vminBase + panY, vmax = vmaxBase + panY;
    var meioV = (vmin + vmax) / 2, faixaV = (vmax - vmin) / zoomY;
    vmin = meioV - faixaV / 2; vmax = meioV + faixaV / 2;

    function yPix(v, clamp) {
      var vc = clamp === false ? v : Math.min(Math.max(v, vmin), vmax);
      return padT + plotH * (1 - (vc - vmin) / (vmax - vmin));
    }
    function xPix(i) { return padL + plotW * ((i - iMin) / (iMax - iMin)); }
    function iDoPix(x) { return iMin + (x - padL) / plotW * (iMax - iMin); }
    function vDoPix(y) { return vmax - (y - padT) / plotH * (vmax - vmin); }

    return { vmin: vmin, vmax: vmax, iMin: iMin, iMax: iMax,
             yPix: yPix, xPix: xPix, iDoPix: iDoPix, vDoPix: vDoPix,
             plotW: plotW, plotH: plotH, padL: padL, padR: padR };
  }

  function desenhar(canvas, candles, linhas, spot, view) {
    var dpr = window.devicePixelRatio || 1;
    var rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    var g = canvas.getContext('2d');
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    var W = rect.width, H = rect.height;
    g.clearRect(0, 0, W, H);

    var grande = W > 700;
    var padL = grande ? 78 : 62, padR = grande ? 20 : 14, padT = grande ? 20 : 14, padB = grande ? 34 : 26;
    var esc = montaEscala(candles, spot, view, W, H, padL, padR, padT, padB);
    var yPix = esc.yPix, xPix = esc.xPix;
    var fonteEixo = grande ? 12 : 10, fonteLabel = grande ? 12 : 10, fonteX = grande ? 11 : 9;

    // recorta o desenho à área do plot: em zoom, candles fora do range de
    // iMin/iMax não devem vazar sobre os eixos.
    g.save();
    g.beginPath(); g.rect(padL, padT, esc.plotW, esc.plotH); g.clip();

    // grade horizontal + eixo de preço
    g.strokeStyle = 'rgba(148,163,184,.12)'; g.fillStyle = '#94a3b8';
    g.font = fonteEixo + 'px sans-serif'; g.textAlign = 'right';
    var passos = 6;
    for (var p = 0; p <= passos; p++) {
      var v = esc.vmin + (esc.vmax - esc.vmin) * (p / passos);
      var y = yPix(v);
      g.beginPath(); g.moveTo(padL, y); g.lineTo(W - padR, y); g.stroke();
    }

    // linhas dos walls/flip/gamma (antes dos candles). Fora do range visível
    // fica tracejada e com seta indicando o lado, sem distorcer a escala.
    linhas.forEach(function (l) {
      var y = yPix(l.valor);
      var fora = l.valor < esc.vmin || l.valor > esc.vmax;
      g.save();
      g.strokeStyle = CORES_WALL[l.cor] || '#a3e635';
      g.lineWidth = fora ? 1 : (l.largura || 1);
      g.globalAlpha = fora ? 0.55 : 1;
      if (l.cor === 'clMidWallFibo' || fora) g.setLineDash([3, 3]);
      g.beginPath(); g.moveTo(padL, y); g.lineTo(W - padR, y); g.stroke();
      if (fora) {
        var seta = l.valor > esc.vmax ? -1 : 1;
        g.fillStyle = g.strokeStyle;
        g.beginPath();
        g.moveTo(padL + 10, y + seta * 5);
        g.lineTo(padL + 5, y);
        g.lineTo(padL + 15, y);
        g.closePath(); g.fill();
      }
      g.restore();
    });

    // candles — só desenha os visíveis na janela atual (zoom/pan)
    var i0 = Math.max(Math.floor(esc.iMin) - 1, 0);
    var i1 = Math.min(Math.ceil(esc.iMax) + 1, candles.length);
    var largura = Math.max(esc.plotW / (esc.iMax - esc.iMin) * 0.6, 1);
    for (var i = i0; i < i1; i++) {
      var c = candles[i];
      var x = xPix(i);
      var alta = c.c >= c.o;
      g.strokeStyle = g.fillStyle = alta ? '#34d399' : '#f87171';
      g.lineWidth = 1;
      g.beginPath(); g.moveTo(x, yPix(c.h)); g.lineTo(x, yPix(c.l)); g.stroke();
      var yo = yPix(c.o), yc = yPix(c.c);
      var top = Math.min(yo, yc), h = Math.max(Math.abs(yc - yo), 1);
      g.fillRect(x - largura / 2, top, largura, h);
    }
    g.restore();   // fim do clip

    // eixo de preço (fora do clip, na margem esquerda)
    g.fillStyle = '#94a3b8'; g.font = fonteEixo + 'px sans-serif'; g.textAlign = 'right';
    for (var p2 = 0; p2 <= passos; p2++) {
      var v2 = esc.vmin + (esc.vmax - esc.vmin) * (p2 / passos);
      g.fillText(fmtEixo(v2), padL - 6, yPix(v2) + 3);
    }

    // eixo X: horário a cada N candles visíveis
    g.fillStyle = '#94a3b8'; g.font = fonteX + 'px sans-serif'; g.textAlign = 'center';
    var passoX = Math.max(Math.ceil((i1 - i0) / 10), 1);
    for (var i2b = i0; i2b < i1; i2b += passoX) {
      if (candles[i2b]) g.fillText(candles[i2b].t, xPix(i2b), H - padB + 14);
    }

    // rótulos das linhas mais relevantes na margem direita
    g.textAlign = 'left'; g.font = '600 ' + fonteLabel + 'px sans-serif';
    linhas.filter(function (l) { return ['clFlip', 'clMaxGamma', 'clMinGamma'].indexOf(l.cor) >= 0; })
      .forEach(function (l) {
        var y = yPix(l.valor);
        g.fillStyle = CORES_WALL[l.cor];
        g.fillText(fmtEixo(l.valor), W - padR - 2, y - 3);
      });

    return esc;   // devolvido para o hover reaproveitar a mesma projeção
  }

  /** Acha a linha (wall/flip/etc.) mais próxima do Y do mouse, dentro de
   * uma tolerância em pixels — usado tanto no tooltip quanto no hover. */
  function achaLinhaProxima(linhas, esc, mouseY, tolPx) {
    var melhor = null, melhorDist = tolPx;
    linhas.forEach(function (l) {
      var y = esc.yPix(l.valor, false);
      var d = Math.abs(y - mouseY);
      if (d < melhorDist) { melhorDist = d; melhor = l; }
    });
    return melhor;
  }

  function achaCandleProximo(candles, esc, mouseX) {
    var i = Math.round(esc.iDoPix(mouseX));
    if (i < 0 || i >= candles.length) return null;
    return { i: i, c: candles[i] };
  }

  /** Liga hover (tooltip) + zoom/pan num canvas. `getView`/`setView` dão
   * acesso ao estado de zoom para o botão de reset e para persistir entre
   * redesenhos; sem eles (modal simples), fica só o tooltip, sem zoom/pan. */
  function ligaInteracao(canvas, tooltipEl, candles, linhas, spot, opts) {
    opts = opts || {};
    var permiteZoom = !!opts.zoom;
    var view = opts.view || { zoomX: 1, zoomY: 1, panX: 0, panY: 0 };
    var arrastando = false, ultimoX = 0, ultimoY = 0;

    function redesenha() {
      return desenhar(canvas, candles, linhas, spot, view);
    }
    var escAtual = redesenha();

    function mostraTooltip(clientX, clientY, texto) {
      var rectWrap = canvas.parentElement.getBoundingClientRect();
      tooltipEl.style.display = 'block';
      tooltipEl.textContent = texto;
      var x = clientX - rectWrap.left + 12, y = clientY - rectWrap.top + 12;
      // evita o tooltip vazar pela direita/baixo do container
      if (x + 160 > rectWrap.width) x = clientX - rectWrap.left - 170;
      if (y + 40 > rectWrap.height) y = clientY - rectWrap.top - 40;
      tooltipEl.style.left = x + 'px';
      tooltipEl.style.top = y + 'px';
    }
    function escondeTooltip() { tooltipEl.style.display = 'none'; }

    canvas.addEventListener('mousemove', function (e) {
      var rect = canvas.getBoundingClientRect();
      var mx = e.clientX - rect.left, my = e.clientY - rect.top;

      if (arrastando && permiteZoom) {
        var dx = mx - ultimoX, dy = my - ultimoY;
        ultimoX = mx; ultimoY = my;
        var nVis = candles.length / view.zoomX;
        view.panX += dx / escAtual.plotW * nVis;
        var faixaV = (escAtual.vmax - escAtual.vmin);
        view.panY += dy / escAtual.plotH * faixaV;
        escAtual = redesenha();
        escondeTooltip();
        return;
      }

      var linha = achaLinhaProxima(linhas, escAtual, my, 6);
      if (linha) {
        mostraTooltip(e.clientX, e.clientY,
          (NOMES_WALL[linha.cor] || 'Linha') + ': ' + fmtEixo(linha.valor));
        return;
      }
      var cand = achaCandleProximo(candles, escAtual, mx);
      if (cand && my >= 0 && my <= rect.height) {
        var c = cand.c;
        mostraTooltip(e.clientX, e.clientY,
          c.t + '  A:' + fmtEixo(c.o) + ' M:' + fmtEixo(c.h) +
          ' m:' + fmtEixo(c.l) + ' F:' + fmtEixo(c.c));
        return;
      }
      escondeTooltip();
    });
    canvas.addEventListener('mouseleave', function () {
      escondeTooltip();
      arrastando = false;
      canvas.style.cursor = permiteZoom ? 'grab' : 'default';
    });

    if (permiteZoom) {
      canvas.addEventListener('mousedown', function (e) {
        arrastando = true; ultimoX = e.clientX - canvas.getBoundingClientRect().left;
        ultimoY = e.clientY - canvas.getBoundingClientRect().top;
        canvas.style.cursor = 'grabbing';
      });
      window.addEventListener('mouseup', function () {
        if (arrastando) { arrastando = false; canvas.style.cursor = 'grab'; }
      });
      canvas.addEventListener('wheel', function (e) {
        e.preventDefault();
        var fator = e.deltaY < 0 ? 1.15 : 1 / 1.15;
        var rectW = canvas.getBoundingClientRect();
        var mxW = e.clientX - rectW.left;
        if (mxW < escAtual.padL) {
          // roda sobre o eixo de valores (margem esquerda): zoom só no eixo Y,
          // mantendo a janela de tempo igual. Ao contrário do zoom em X (que
          // só estreita, já que abrir além do dia inteiro não faz sentido),
          // aqui zoomY pode cair abaixo de 1 — é isso que abre a faixa de
          // preço para revelar walls mais distantes do candle do dia.
          view.zoomY = Math.min(Math.max(view.zoomY * fator, 0.1), 40);
        } else {
          view.zoomX = Math.min(Math.max(view.zoomX * fator, 1), 40);
        }
        escAtual = redesenha();
      }, { passive: false });
      canvas.addEventListener('dblclick', function () {
        view.zoomX = 1; view.zoomY = 1; view.panX = 0; view.panY = 0;
        escAtual = redesenha();
      });
      canvas.style.cursor = 'grab';
    }

    // Redesenha ao redimensionar a janela (o modal expandido muda de
    // tamanho conforme o viewport).
    var ro = new ResizeObserver(function () { escAtual = redesenha(); });
    ro.observe(canvas.parentElement);

    return { view: view, resetar: function () {
      view.zoomX = 1; view.zoomY = 1; view.panX = 0; view.panY = 0; escAtual = redesenha();
    } };
  }

  function montaLegendaHTML() {
    return '<span><i style="display:inline-block;width:10px;height:10px;background:#a3e635;border-radius:2px;"></i> Walls</span>' +
      '<span><i style="display:inline-block;width:10px;height:10px;background:#94a3b8;border-radius:2px;"></i> MidWall</span>' +
      '<span><i style="display:inline-block;width:10px;height:2px;background:#475569;"></i> Fibo 11,8%</span>' +
      '<span><i style="display:inline-block;width:10px;height:10px;background:#facc15;border-radius:2px;"></i> Flip</span>' +
      '<span><i style="display:inline-block;width:10px;height:10px;background:#34d399;border-radius:2px;"></i> Gama máx.</span>' +
      '<span><i style="display:inline-block;width:10px;height:10px;background:#f87171;border-radius:2px;"></i> Gama mín.</span>';
  }

  function abrirExpandido() {
    if (!_ultimoEstado) return;
    ensureModalGrande();
    _modalGrande.style.display = 'flex';
    document.getElementById('wcmg-titulo').textContent = '📈 ' + _ultimoEstado.titulo;
    document.getElementById('wcmg-sub').textContent = _ultimoEstado.sub;
    document.getElementById('wcmg-legenda').innerHTML = montaLegendaHTML();

    var canvas = document.getElementById('wcmg-canvas');
    var tooltip = document.getElementById('wcmg-tooltip');
    requestAnimationFrame(function () {
      var lig = ligaInteracao(canvas, tooltip, _ultimoEstado.candles,
        _ultimoEstado.linhas, _ultimoEstado.spot, { zoom: true });
      document.getElementById('wcmg-reset').onclick = lig.resetar;
    });
  }

  /**
   * Abre o modal, busca os candles de 5min do dia informado e desenha o
   * gráfico com os walls do payload `d` sobrepostos.
   *
   * @param {Object} opts
   *   titulo    string exibido no cabeçalho
   *   endpoint  URL do backend (/api/walls-candles/IND?dia=... ou
   *             .../PETR4?...&simbolo=PETR4)
   *   dados     payload da API (mesmo formato usado por gerarWallsNTSL)
   *   dia       YYYY-MM-DD do pregão a mostrar
   *   spot      preço de referência do momento do cálculo (linha azul)
   */
  function abrirGraficoWalls(opts) {
    ensureModal();
    _modal.style.display = 'flex';
    document.getElementById('wcm-titulo').textContent = '📈 ' + opts.titulo;
    document.getElementById('wcm-sub').textContent = '';
    document.getElementById('wcm-legenda').innerHTML = '';
    document.getElementById('wcm-canvas-wrap').style.display = 'none';
    var elStatus = document.getElementById('wcm-status');
    elStatus.style.display = 'block';
    elStatus.textContent = '⏳ Buscando candles de 5min…';

    fetch(opts.endpoint)
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) {
          elStatus.textContent = '⚠️ ' + (res.j.error || 'Erro ao buscar candles.');
          return;
        }
        var j = res.j;
        var top16 = extrairTop16Walls(opts.dados);
        var linhas = top16.map(function (p) {
          return { valor: p.strike, cor: 'clWall', largura: p.largura };
        });
        for (var i = 0; i < top16.length - 1; i++) {
          var a = top16[i].strike, b = top16[i + 1].strike;
          var passo = b - a, meio = (a + b) / 2, banda = passo * 0.118;
          linhas.push({ valor: meio, cor: 'clMidWall', largura: 1 });
          linhas.push({ valor: meio - banda, cor: 'clMidWallFibo', largura: 1 });
          linhas.push({ valor: meio + banda, cor: 'clMidWallFibo', largura: 1 });
        }
        if (opts.dados.gamma_max && isFinite(opts.dados.gamma_max.s)) {
          linhas.push({ valor: opts.dados.gamma_max.s, cor: 'clMaxGamma', largura: 2 });
        }
        if (opts.dados.gamma_min && isFinite(opts.dados.gamma_min.s)) {
          linhas.push({ valor: opts.dados.gamma_min.s, cor: 'clMinGamma', largura: 2 });
        }
        if (isFinite(opts.dados.flip)) {
          linhas.push({ valor: opts.dados.flip, cor: 'clFlip', largura: 2 });
        }

        var p = (j.dia || '').split('-');
        var sub = j.nome + ' · ' + j.simbolo + ' · pregão de ' +
          (p.length === 3 ? (p[2] + '/' + p[1] + '/' + p[0]) : j.dia) +
          ' · ' + j.candles.length + ' candles de 5min';
        document.getElementById('wcm-sub').textContent = sub;
        document.getElementById('wcm-legenda').innerHTML = montaLegendaHTML();

        elStatus.style.display = 'none';
        var wrap = document.getElementById('wcm-canvas-wrap');
        wrap.style.display = 'block';
        var canvas = document.getElementById('wcm-canvas');
        var tooltip = document.getElementById('wcm-tooltip');

        _ultimoEstado = { titulo: opts.titulo, sub: sub, candles: j.candles,
                          linhas: linhas, spot: opts.spot };

        // Espera o layout aplicar display:block antes de medir o wrap.
        requestAnimationFrame(function () {
          ligaInteracao(canvas, tooltip, j.candles, linhas, opts.spot, { zoom: false });
        });
      })
      .catch(function (err) {
        elStatus.textContent = '⚠️ Falha ao carregar: ' + ((err && err.message) || err);
      });
  }

  global.abrirGraficoWalls = abrirGraficoWalls;
})(window);
