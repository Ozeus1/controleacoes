/* Modal "Ver Gráfico": candles de 5min do dia seguinte ao cálculo dos
 * Walls, com os principais walls e o Flip desenhados como linhas
 * horizontais — leitura visual de onde o gama concentrado bateu contra o
 * preço real no pregão em que o indicador passou a valer.
 *
 * Candlestick desenhado em canvas puro (sem lib externa), no mesmo espírito
 * do MyChart já usado no projeto — mas dedicado e simples, porque o caso é
 * bem mais restrito: um dia fixo, sem pan/zoom/ferramentas de desenho.
 */
(function (global) {
  'use strict';

  var _modal = null;

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
      '    <button type="button" id="wcm-fechar" style="background:none;border:none;font-size:1.3rem;' +
      '            color:var(--text-secondary,#94a3b8);cursor:pointer;line-height:1;">✕</button>' +
      '  </div>' +
      '  <p id="wcm-sub" style="margin:0 0 .6rem;font-size:.82rem;color:var(--text-secondary,#94a3b8);"></p>' +
      '  <div id="wcm-legenda" style="display:flex;gap:1rem;flex-wrap:wrap;font-size:.78rem;' +
      '       color:var(--text-secondary,#94a3b8);margin-bottom:.5rem;"></div>' +
      '  <div id="wcm-status" style="text-align:center;padding:2rem;color:var(--text-secondary,#94a3b8);"></div>' +
      '  <div id="wcm-canvas-wrap" style="position:relative;height:460px;display:none;">' +
      '    <canvas id="wcm-canvas" style="width:100%;height:100%;display:block;"></canvas>' +
      '  </div>' +
      '</div>';
    document.body.appendChild(_modal);
    document.getElementById('wcm-fechar').onclick = fechar;
    _modal.addEventListener('click', function (e) { if (e.target === _modal) fechar(); });
  }

  function fechar() {
    if (_modal) _modal.style.display = 'none';
  }

  var CORES_WALL = { clWall: '#a3e635', clMidWall: '#94a3b8', clMidWallFibo: '#475569',
                     clFlip: '#facc15', clMaxGamma: '#34d399', clMinGamma: '#f87171' };

  function desenhar(canvas, candles, linhas, spot) {
    var dpr = window.devicePixelRatio || 1;
    var rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    var g = canvas.getContext('2d');
    g.scale(dpr, dpr);
    var W = rect.width, H = rect.height;
    g.clearRect(0, 0, W, H);

    var padL = 62, padR = 14, padT = 14, padB = 26;
    var plotW = W - padL - padR, plotH = H - padT - padB;

    // A escala prioriza o range real do dia — walls de vencimentos longos
    // costumam ficar bem mais dispersos que a variação de um único pregão
    // (ex.: walls de 180 a 215 mil contra um candle oscilando só entre 183
    // e 186 mil) e, se entrassem no cálculo do range, esmagariam os candles
    // numa linha reta. Os que caem fora aparecem "grudados" na borda de
    // cima/baixo do gráfico (clamp), visíveis como referência sem distorcer.
    var valsCandle = [];
    candles.forEach(function (c) { valsCandle.push(c.h, c.l); });
    if (spot) valsCandle.push(spot);
    var vmin = Math.min.apply(null, valsCandle), vmax = Math.max.apply(null, valsCandle);
    var folga = (vmax - vmin) * 0.10 || Math.abs(vmin) * 0.01 || 1;
    vmin -= folga; vmax += folga;

    function yPix(v) {
        var vc = Math.min(Math.max(v, vmin), vmax);   // clamp p/ linhas fora do range
        return padT + plotH * (1 - (vc - vmin) / (vmax - vmin));
    }
    function xPix(i) { return padL + plotW * ((i + 0.5) / candles.length); }

    // grade horizontal + eixo de preço
    g.strokeStyle = 'rgba(148,163,184,.12)'; g.fillStyle = '#94a3b8';
    g.font = '10px sans-serif'; g.textAlign = 'right';
    var passos = 6;
    for (var p = 0; p <= passos; p++) {
      var v = vmin + (vmax - vmin) * (p / passos);
      var y = yPix(v);
      g.beginPath(); g.moveTo(padL, y); g.lineTo(W - padR, y); g.stroke();
      g.fillText(fmtEixo(v), padL - 6, y + 3);
    }

    // linhas dos walls/flip/gamma (desenhadas antes dos candles). Uma linha
    // fora do range real do dia fica "grudada" na borda (yPix já clampeia) —
    // desenhada tracejada e mais fina, com uma seta indicando para que lado
    // o valor real está, em vez de parecer uma linha comum dentro do range.
    linhas.forEach(function (l) {
      var y = yPix(l.valor);
      var fora = l.valor < vmin || l.valor > vmax;
      g.save();
      g.strokeStyle = CORES_WALL[l.cor] || '#a3e635';
      g.lineWidth = fora ? 1 : (l.largura || 1);
      g.globalAlpha = fora ? 0.55 : 1;
      if (l.cor === 'clMidWallFibo' || fora) g.setLineDash([3, 3]);
      g.beginPath(); g.moveTo(padL, y); g.lineTo(W - padR, y); g.stroke();
      if (fora) {
        var seta = l.valor > vmax ? -1 : 1;   // aponta pra fora da área útil
        g.fillStyle = g.strokeStyle;
        g.beginPath();
        g.moveTo(padL + 10, y + seta * 5);
        g.lineTo(padL + 5, y);
        g.lineTo(padL + 15, y);
        g.closePath(); g.fill();
      }
      g.restore();
    });

    // candles
    var largura = Math.max(plotW / candles.length * 0.6, 1);
    candles.forEach(function (c, i) {
      var x = xPix(i);
      var alta = c.c >= c.o;
      g.strokeStyle = g.fillStyle = alta ? '#34d399' : '#f87171';
      g.lineWidth = 1;
      g.beginPath(); g.moveTo(x, yPix(c.h)); g.lineTo(x, yPix(c.l)); g.stroke();
      var yo = yPix(c.o), yc = yPix(c.c);
      var top = Math.min(yo, yc), h = Math.max(Math.abs(yc - yo), 1);
      g.fillRect(x - largura / 2, top, largura, h);
    });

    // eixo X: horário a cada N candles
    g.fillStyle = '#94a3b8'; g.font = '9px sans-serif'; g.textAlign = 'center';
    var passoX = Math.max(Math.ceil(candles.length / 10), 1);
    for (var i2 = 0; i2 < candles.length; i2 += passoX) {
      g.fillText(candles[i2].t, xPix(i2), H - padB + 14);
    }

    // rótulos das linhas mais relevantes (Flip/Max/Min) na margem direita
    g.textAlign = 'left'; g.font = '600 10px sans-serif';
    linhas.filter(function (l) { return ['clFlip', 'clMaxGamma', 'clMinGamma'].indexOf(l.cor) >= 0; })
      .forEach(function (l) {
        var y = yPix(l.valor);
        g.fillStyle = CORES_WALL[l.cor];
        g.fillText(fmtEixo(l.valor), W - padR - 2, y - 3);
      });
  }

  function fmtEixo(v) {
    return v >= 1000 ? Math.round(v).toLocaleString('pt-BR') : Number(v).toFixed(2).replace('.', ',');
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
        document.getElementById('wcm-sub').textContent =
          j.nome + ' · ' + j.simbolo + ' · pregão de ' + (p.length === 3 ? (p[2] + '/' + p[1] + '/' + p[0]) : j.dia) +
          ' · ' + j.candles.length + ' candles de 5min';
        document.getElementById('wcm-legenda').innerHTML =
          '<span><i style="display:inline-block;width:10px;height:10px;background:#a3e635;border-radius:2px;"></i> Walls</span>' +
          '<span><i style="display:inline-block;width:10px;height:10px;background:#94a3b8;border-radius:2px;"></i> MidWall</span>' +
          '<span><i style="display:inline-block;width:10px;height:2px;background:#475569;"></i> Fibo 11,8%</span>' +
          '<span><i style="display:inline-block;width:10px;height:10px;background:#facc15;border-radius:2px;"></i> Flip</span>' +
          '<span><i style="display:inline-block;width:10px;height:10px;background:#34d399;border-radius:2px;"></i> Gama máx.</span>' +
          '<span><i style="display:inline-block;width:10px;height:10px;background:#f87171;border-radius:2px;"></i> Gama mín.</span>';

        elStatus.style.display = 'none';
        var wrap = document.getElementById('wcm-canvas-wrap');
        wrap.style.display = 'block';
        var canvas = document.getElementById('wcm-canvas');
        // Espera o layout aplicar display:block antes de medir o wrap.
        requestAnimationFrame(function () {
          desenhar(canvas, j.candles, linhas, opts.spot);
        });
      })
      .catch(function (err) {
        elStatus.textContent = '⚠️ Falha ao carregar: ' + ((err && err.message) || err);
      });
  }

  global.abrirGraficoWalls = abrirGraficoWalls;
})(window);
